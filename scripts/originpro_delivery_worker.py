"""Owned-process adapter for renderer save capture and saved-project readback."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import runpy
import sys
from delivery_contract import read, write, validate
from origin_readback import snapshot, compare, install_save_hook, apply_profile, export_all, preservation_expectations

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor/editaplot/runtime/src'))


def finalize(contract, directory):
    from origin_sciplot.origin_backend.session import OriginSession
    project = directory / 'result.opju'
    profile = contract['presentation']['profile']
    report = {'pass': False, 'stage': 'reopen_renderer_output'}
    try:
        with OriginSession(keep_open=False) as session:
            op = session.op
            if not project.is_file() or not op.open(str(project), readonly=True, asksave=False):
                raise RuntimeError('Could not open the saved renderer project')
            initial = snapshot(op)
            report['renderer_save_roundtrip'] = compare(read(directory / 'before-save.json'), initial)
            if not report['renderer_save_roundtrip']['pass']:
                raise RuntimeError('Renderer saved-state readback mismatch')
            if (directory/'curve-style-report.json').is_file():
                curve = read(directory/'curve-style-report.json')
                report['curve_preset_saved_style'] = compare(curve['expected'], initial, subset=True)
                if not report['curve_preset_saved_style']['pass']:
                    raise RuntimeError('Curve preset did not survive save/reopen')
                # Each component's next plot is a no-line reference to its explicit background.
                values = initial['values']
                report['fill_target_bindings'] = []
                for item in curve['mapping']:
                    if 'fill_target_plot' not in item: continue
                    helper = item['fill_target_plot']
                    hp = f'g1/l1/p{helper}/'
                    background = next((m for m in curve['mapping'] if not m['auxiliary'] and
                                       m['y_column']==curve['mapping'][helper-1]['y_column']), None)
                    passed = values[f"g1/l1/p{item['plot']}/fill_target_offset"]==0 and values[hp+'line_connect']==0
                    if background:
                        bp=f"g1/l1/p{background['plot']}/"
                        passed = passed and values[hp+'x_range']==values[bp+'x_range'] and values[hp+'y_range']==values[bp+'y_range']
                    report['fill_target_bindings'].append({'component':item['name'],'helper_plot':helper,'pass':passed})
                    if not passed: raise RuntimeError('Saved gradient target binding changed')
            # Profiles are applied after upstream rendering checks; their own checks follow a second reopen.
            requested = apply_profile(op, profile)
            before = snapshot(op)
            report['requested_style'] = compare(requested, before, subset=True)
            if (directory/'template-baseline.json').is_file():
                preserved = preservation_expectations(read(directory/'template-baseline.json'),
                                                     read(directory/'native-job.json'), profile)
                report['template_preservation'] = compare(preserved, before, subset=True)
                if not report['template_preservation']['pass']:
                    raise RuntimeError('Unrequested template style changed')
            if not report['requested_style']['pass']:
                raise RuntimeError('Requested style did not apply')
            # Readonly protects the input on open; save the modified copy to a new owned path.
            final_project = directory/'final.opju'
            op.save(str(final_project))
            op.new()
            if not op.open(str(final_project), readonly=True, asksave=False):
                raise RuntimeError('Could not reopen the final project')
            actual = snapshot(op)
            write(directory/'saved-state.json', actual)
            report['final_save_roundtrip'] = compare(before, actual)
            if not report['final_save_roundtrip']['pass']:
                raise RuntimeError('Final saved-state readback mismatch')
            # Export only from the reopened final project; the project stays byte-identical during export.
            report['exports'] = export_all(op, directory, profile)
            report['environment'] = session.environment.to_dict()
        final_project.replace(project)
        report['pass'] = True
        report['stage'] = 'complete'
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        write(directory/'readback-report.json', report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['native', 'routes', 'finalize'])
    parser.add_argument('contract')
    parser.add_argument('directory')
    parser.add_argument('--backend', default='auto', choices=['auto', 'cli', 'com'])
    parser.add_argument('--origin-exe')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--cli-startup-timeout', type=int, default=60)
    args, remaining = parser.parse_known_args()
    directory = Path(args.directory).resolve()
    contract = read(args.contract)
    validate(contract)
    if args.mode == 'finalize':
        finalize(contract, directory)
    else:
        os.environ['ORIGINPRO_DELIVERY_DIR'] = str(directory)
        import originpro as op
        install_save_hook(op, directory, refresh_layout=args.mode == 'native')
        if args.mode == 'routes':
            sys.argv = ['origin_sciplot.workers.run_template_worker', *remaining]
            runpy.run_module('origin_sciplot.workers.run_template_worker', run_name='__main__')
        else:
            import originpro_build as native
            job = native.validate_job(directory/'native-job.json')
            result = native.run_selected_backend(job, 'build', args.backend, args.origin_exe,
                                                 args.timeout, args.cli_startup_timeout, False)
            write(directory/'native-build-report.json', result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
