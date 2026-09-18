#!/usr/bin/env python
"""The 40-route extension for originpro-cli-plot, using pinned EditaPlot source.

Both render entry points share the source-bound delivery and saved-state checks.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

SKILL = Path(__file__).resolve().parents[1]
VENDOR = SKILL / 'vendor' / 'editaplot'
ENGINE = VENDOR / 'runtime'
CLI = VENDOR / 'cli'
COMMANDS = {
    'doctor', 'catalog', 'palettes', 'inspect', 'start', 'recommend', 'understand',
    'plan', 'origin-smoke', 'render', 'verify', 'reference-inspect',
    'reference-review', 'panel-plan',
}


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def load_core():
    sys.path.insert(0, str(CLI))
    import editaplot_core
    return editaplot_core


def check_install() -> dict:
    manifest = json.loads((VENDOR / 'UPSTREAM.json').read_text(encoding='utf-8'))
    problems = []
    for rel, expected in manifest['sha256'].items():
        p = (VENDOR / rel).resolve()
        if not p.is_relative_to(VENDOR.resolve()):
            problems.append({'path': rel, 'problem': 'invalid_manifest_path'})
        elif not p.is_file():
            problems.append({'path': rel, 'problem': 'missing'})
        elif hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            problems.append({'path': rel, 'problem': 'hash_mismatch'})
    return {'ok': not problems, 'upstream_commit': manifest['commit'],
            'public_route_count': len(manifest['public_routes']),
            'checked_files': len(manifest['sha256']), 'problems': problems}


def catalog(as_json: bool) -> None:
    result = load_core().catalog(engine_home=ENGINE)
    result['skill'] = 'originpro-cli-plot'
    result['local_origin_validation'] = 'Requires current-host smoke, render, readback and visual QA.'
    for route in result['templates']:
        route['upstream_support_level'] = route.pop('support_level')
    if as_json:
        emit(result)
    else:
        print(f"originpro-cli-plot: {len(result['templates'])} bundled Origin routes")
        print('Upstream verification is separate from verification on this computer.\n')
        for i, route in enumerate(result['templates'], 1):
            print(f"{i:02d}. {route['id']:<24} {route['name']}")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {'-h', '--help'}:
        print('OriginPro CLI Plot — 40-route extension')
        print('Usage: python scripts/originpro_routes.py COMMAND [arguments]')
        print('Commands: catalog [--json], check-install, validate-plan PLAN.json,')
        print('          doctor [--repair], start, inspect, recommend, understand, plan,')
        print('          palettes, origin-smoke, render, verify, reference-inspect,')
        print('          reference-review, panel-plan')
        print('Use COMMAND --help for data/plan/render arguments.')
        print('Existing OPJU template jobs use scripts/originpro_build.py.')
        return 0
    if args[0] == 'check-install':
        result = check_install()
        emit(result)
        return 0 if result['ok'] else 1
    # A repaired environment is private to this engine; never change system Python or PATH.
    managed = ENGINE / '.editaplot-venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    repairing = args[0] == 'doctor' and '--repair' in args
    if managed.is_file() and not repairing and Path(sys.executable).resolve() != managed.resolve():
        return subprocess.run([str(managed), '-X', 'utf8', str(Path(__file__).resolve()), *args],
                              check=False).returncode
    if args[0] == 'catalog':
        if args[1:] not in ([], ['--json']):
            raise ValueError('Use catalog or catalog --json.')
        catalog('--json' in args)
        return 0
    if args[0] == 'validate-plan':
        if len(args) != 2:
            raise ValueError('Usage: validate-plan PLAN.json')
        core = load_core()
        core.bootstrap_engine(ENGINE)
        plan = core.load_json(args[1])
        core.validate_plan(plan)  # Includes the frozen semantic contract and current source hash.
        emit({'ok': True, 'template_id': plan['template']['id'],
              'source_sha256': plan['source']['sha256'], 'origin_launched': False})
        return 0
    if args[0] not in COMMANDS:
        raise ValueError(f'Unknown command: {args[0]}')
    if args[0] == 'render':
        import argparse
        parser = argparse.ArgumentParser(description='Render through shared confirmation and saved-project checks')
        parser.add_argument('plan_file')
        parser.add_argument('--contract', required=True)
        parser.add_argument('--output-dir')
        parser.add_argument('--close-origin', action='store_true', help='Owned workers always close after saved-state verification')
        options = parser.parse_args(args[1:])
        from delivery_contract import read
        from originpro_delivery import run
        record = read(options.contract)
        if record['backend'] != 'routes' or Path(record['input']).resolve() != Path(options.plan_file).resolve():
            raise ValueError('Delivery record does not match the render plan')
        emit(run(options.contract, options.output_dir))
        return 0
    if args[0] == 'verify' and len(args) >= 2 and (Path(args[1])/'delivery-manifest.json').is_file():
        from originpro_delivery import verify
        result = verify(args[1])
        emit(result)
        return 0 if result['programmatic_pass'] else 1
    if any(a == '--engine-home' or a.startswith('--engine-home=') for a in args):
        raise ValueError('This entry point uses its bundled engine; --engine-home is not accepted.')
    sys.path.insert(0, str(CLI))
    import editaplot
    if args[0] not in {'verify', 'panel-plan'}:
        args.extend(['--engine-home', str(ENGINE)])
    # Keep the worker on the selected interpreter rather than inheriting a different engine's override.
    if args[0] in {'render', 'origin-smoke'} and not any(
            a == '--python' or a.startswith('--python=') for a in args):
        args.extend(['--python', sys.executable])
    return editaplot.main(args)


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    try:
        raise SystemExit(main())
    except (ValueError, OSError, ImportError, KeyError, RuntimeError) as exc:
        emit({'ok': False, 'error': type(exc).__name__, 'message': str(exc)})
        raise SystemExit(1)
