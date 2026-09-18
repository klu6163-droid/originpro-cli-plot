#!/usr/bin/env python
"""Shared source-bound confirmation, saved-state readback and four-format delivery."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime
import delivery_contract as dc

ROOT = Path(__file__).resolve().parents[1]


def checked_process(command, directory, log_name, env=None):
    with (directory/log_name).open('w', encoding='utf-8') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=env, check=False)
    if result.returncode:
        raise RuntimeError(f'Origin worker failed ({result.returncode}); see {directory/log_name}')


def verify(directory):
    directory = Path(directory).resolve()
    manifest = dc.read(directory/'delivery-manifest.json')
    dc.check_seal(manifest)
    dc.validate(dc.read(directory/'task-record.json'), check_engine=False)
    failures = []
    for f in manifest['artifacts']:
        try:
            if dc.file_record(f['path'], f['role'])['sha256'] != f['sha256']:
                failures.append('Changed artifact: '+f['path'])
        except OSError:
            failures.append('Missing artifact: '+f['path'])
    visual = None
    if (directory/'visual-review.json').is_file():
        visual = dc.read(directory/'visual-review.json')
        dc.check_seal(visual)
        if visual.get('manifest_sha256') != manifest['record_sha256']:
            failures.append('Visual review belongs to another output manifest')
    programmatic = manifest['programmatic_pass'] and not failures
    return {'programmatic_pass': programmatic,
            'complete': bool(programmatic and visual and visual['pass']),
            'visual_status': 'passed' if visual and visual['pass'] else 'pending_or_failed',
            'failures': failures, 'directory': str(directory)}


def run(contract_path, output_dir=None, *, backend='auto', origin_exe=None,
        timeout=180, cli_startup_timeout=60):
    contract_path = Path(contract_path).resolve(strict=True)
    contract = dc.read(contract_path)
    dc.validate(contract)
    # Check dependencies and vendor integrity before launching Origin.
    import PIL
    import pypdf
    import originpro_routes as routes
    if not routes.check_install()['ok']:
        raise RuntimeError('Bundled engine integrity check failed')
    source = Path(contract['input'])
    directory = Path(output_dir or source.with_name(source.stem+'_delivery_'+datetime.now().strftime('%Y%m%d_%H%M%S'))).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    dc.write(directory/'task-record.json', contract)
    worker = Path(__file__).with_name('originpro_delivery_worker.py')
    entry = [sys.executable, '-X', 'utf8', str(worker)]
    status = {'pass': False, 'stage': 'render'}
    try:
        if contract['backend'] == 'native':
            spec = dc.read(source)
            inputs = directory/'inputs'
            inputs.mkdir()
            for f in contract['files']:
                if f['role'] not in ('plotted_source', 'template', 'style'):
                    continue
                target = inputs/(f['role']+Path(f['path']).suffix)
                shutil.copy2(f['path'], target)
                if dc.file_record(target, f['role'])['sha256'] != f['sha256']:
                    raise RuntimeError('Input changed while making the execution snapshot')
                if f['role'] == 'style':
                    spec['graph']['style_file'] = str(target)
                else:
                    spec[{'plotted_source':'data_csv','template':'template_opju'}[f['role']]] = str(target)
            spec.update(output_opju=str(directory/'result.opju'), qa_png=str(directory/'engine-preview.png'), overwrite=False)
            dc.write(directory/'native-job.json', spec)
            command = entry+['native', str(contract_path), str(directory), '--backend', backend,
                             '--timeout', str(timeout), '--cli-startup-timeout', str(cli_startup_timeout)]
            if origin_exe:
                command += ['--origin-exe', origin_exe]
            checked_process(command, directory, 'render.log')
        else:
            core = routes.load_core()
            plan = dc.read(source)
            command, env, _ = core.build_worker_command(plan, plan_file=str(source),
                engine_home=routes.ENGINE, python_executable=sys.executable,
                output_dir=str(directory/'engine'), close_origin=True)
            # Replace only the module entry; all upstream plan/digest validation arguments are retained.
            module_index = command.index('-m')
            command = command[:module_index]+[str(worker), 'routes', str(contract_path), str(directory)]+command[module_index+2:]
            checked_process(command, directory, 'render.log', env)
            shutil.copy2(directory/'engine/result.opju', directory/'result.opju')
            shutil.copy2(directory/'engine/origin_verify_report.json', directory/'origin_verify_report.json')
        dc.validate(contract)  # Catch source/template changes during rendering.
        status['stage'] = 'saved_project_readback_and_export'
        checked_process(entry+['finalize', str(contract_path), str(directory)], directory, 'readback.log')
        dc.validate(contract)
        from artifact_verification import inspect_export
        readback = dc.read(directory/'readback-report.json')
        reports = [inspect_export(item, contract['presentation']['profile']) for item in readback['exports']]
        dc.write(directory/'export-report.json', reports)
        if not all(r['pass_'] for r in reports):
            raise RuntimeError('Export content verification failed; see export-report.json')
        # Compatibility aliases are written only after all saved-state/export checks pass.
        aliases = []
        if contract['backend'] == 'native':
            spec = contract['presentation']['input']
            protected = {Path(f['path']).resolve() for f in contract['files']}
            for key, rendered in (('output_opju', 'result.opju'), ('qa_png', 'result.png')):
                if not spec.get(key):
                    continue
                dest = (source.parent/Path(spec[key])).resolve()
                if dest in protected:
                    raise RuntimeError('Output alias would overwrite a bound input')
                if dest.exists() and not spec.get('overwrite', False):
                    raise RuntimeError('Output alias exists without overwrite authorization: '+str(dest))
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(directory/rendered, dest)
                aliases.append(dc.file_record(dest, 'compatibility_alias'))
        artifact_paths = [directory/'result.opju', directory/'task-record.json', directory/'saved-state.json',
                          directory/'before-save.json', directory/'readback-report.json', directory/'export-report.json']
        artifact_paths += [Path(item['path']) for item in readback['exports']]
        if (directory/'inputs').is_dir():
            artifact_paths += list((directory/'inputs').iterdir())
        for name in ('template-baseline.json', 'native-build-report.json', 'origin_verify_report.json', 'curve-style-report.json'):
            if (directory/name).is_file():
                artifact_paths.append(directory/name)
        manifest = {'schema': dc.SCHEMA, 'programmatic_pass': True, 'visual_status': 'pending',
                    'science_sha256': contract['science_sha256'], 'presentation_sha256': contract['presentation_sha256'],
                    'task_record_sha256': contract['record_sha256'],
                    'required_formats': ['opju', 'png', 'pdf', 'tif'],
                    'artifacts': [dc.file_record(p, p.suffix[1:]) for p in artifact_paths]+aliases}
        dc.write(directory/'delivery-manifest.json', dc.seal(manifest))
        status.update({'pass': True, 'stage': 'programmatic_pass_visual_pending'})
        return verify(directory)
    except Exception as exc:
        status['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        dc.write(directory/'run-status.json', status)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare', help='Create a draft; never invent user confirmation')
    prep.add_argument('--backend', choices=['native', 'routes'], required=True)
    prep.add_argument('--input', required=True)
    prep.add_argument('--profile', help='Optional presentation JSON')
    prep.add_argument('--source', action='append', default=[], help='Original acquisition file(s), before CSV export')
    prep.add_argument('--provenance', help='JSON describing sheet, units, errors and processing')
    prep.add_argument('--reuse', help='Previous confirmed record; science digest must match')
    prep.add_argument('--output', required=True)
    conf = sub.add_parser('confirm', help='Record an actual, already-given user choice')
    conf.add_argument('record')
    conf.add_argument('--statement', required=True)
    conf.add_argument('--context', required=True)
    conf.add_argument('--kind', choices=['user', 'test_fixture'], default='user')
    conf.add_argument('--output', required=True)
    val = sub.add_parser('validate')
    val.add_argument('record')
    runner = sub.add_parser('run')
    runner.add_argument('record')
    runner.add_argument('--output-dir')
    runner.add_argument('--backend', choices=['auto', 'cli', 'com'], default='auto')
    runner.add_argument('--origin-exe')
    runner.add_argument('--timeout', type=int, default=180)
    runner.add_argument('--cli-startup-timeout', type=int, default=60)
    ver = sub.add_parser('verify')
    ver.add_argument('directory')
    review = sub.add_parser('record-visual', help='After viewing every final graph, record the review')
    review.add_argument('directory')
    review.add_argument('--reviewer', required=True)
    review.add_argument('--notes', required=True)
    review.add_argument('--result', choices=['pass', 'fail'], required=True)
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        value = dc.prepare(args.backend, args.input, dc.read(args.profile) if args.profile else None,
            args.source, dc.read(args.provenance) if args.provenance else None, args.reuse)
        _safe_record_write(args.output, value, [args.input, args.reuse, args.profile, args.provenance, *args.source])
        return {'record': args.output, 'science_sha256': value['science_sha256'], 'confirmed': bool(value['confirmation'])}
    if args.command == 'confirm':
        value = dc.confirm(dc.read(args.record), args.statement, args.context, args.kind)
        _safe_record_write(args.output, value, [args.record])
        return {'record': args.output, 'confirmed': True, 'kind': args.kind}
    if args.command == 'validate':
        return {'valid': dc.validate(dc.read(args.record)), 'origin_launched': False}
    if args.command == 'run':
        return run(args.record, args.output_dir, backend=args.backend, origin_exe=args.origin_exe,
                   timeout=args.timeout, cli_startup_timeout=args.cli_startup_timeout)
    if args.command == 'verify':
        return verify(args.directory)
    directory = Path(args.directory)
    result = verify(directory)
    if not result['programmatic_pass']:
        raise ValueError('Cannot record visual acceptance before programmatic verification passes')
    if not args.reviewer.strip() or not args.notes.strip():
        raise ValueError('Visual review needs reviewer identity and observations')
    manifest = dc.read(directory/'delivery-manifest.json')
    dc.write(directory/'visual-review.json', dc.seal({'pass': args.result == 'pass',
             'reviewer': args.reviewer, 'notes': args.notes,
             'manifest_sha256': manifest['record_sha256'], 'recorded_at': datetime.now().astimezone().isoformat()}))
    return verify(directory)


def _safe_record_write(path, value, other_inputs):
    destination = Path(path).resolve()
    protected = {Path(f['path']).resolve() for f in value['files']}
    protected.update(Path(p).resolve() for p in other_inputs if p)
    if destination in protected or destination.exists():
        raise ValueError('Use a new task-record path; do not overwrite input or previous evidence')
    dc.write(destination, value)


if __name__ == '__main__':
    managed = ROOT/'vendor/editaplot/runtime/.editaplot-venv'/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if managed.is_file() and managed.resolve() != Path(sys.executable).resolve():
        raise SystemExit(subprocess.call([str(managed), '-X', 'utf8', __file__, *sys.argv[1:]]))
    try:
        value = main()
        print(json.dumps(value, ensure_ascii=False, indent=2))
        raise SystemExit(0 if value.get('programmatic_pass', True) else 2)
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': f'{type(exc).__name__}: {exc}'}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
