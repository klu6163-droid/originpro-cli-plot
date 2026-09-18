"""Source-bound task records shared by both Origin backends (no Origin imports)."""
from __future__ import annotations
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 'originpro-delivery/2'
ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def file_record(path, role):
    p = Path(path).resolve(strict=True)
    return {'role': role, 'path': str(p), 'bytes': p.stat().st_size,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def engine_record():
    paths = sorted((ROOT / 'scripts').glob('*.py')) + [ROOT / 'vendor/editaplot/UPSTREAM.json']
    files = {p.relative_to(ROOT).as_posix(): file_record(p, 'code')['sha256'] for p in paths}
    return {'upstream_commit': read(ROOT / 'vendor/editaplot/UPSTREAM.json')['commit'],
            'adapter_sha256': digest(files), 'files': files}


def seal(record):
    record['record_sha256'] = digest({k: v for k, v in record.items() if k != 'record_sha256'})
    return record


def check_seal(record):
    if record.get('record_sha256') != digest({k: v for k, v in record.items() if k != 'record_sha256'}):
        raise ValueError('Task record changed; prepare a new record before reuse.')


def profile_defaults(profile=None):
    p = {'dpi': 300, 'tiff_compression': 'LZW', 'required_formats': ['opju', 'png', 'pdf', 'tif'],
         'pdf_text_required': True, 'pdf_embedded_fonts_required': True,
         'allow_full_page_raster': False, 'expected': {}}
    p.update(profile or {})
    allowed = set(profile_defaults.__dict__.get('extra', []))  # set below; rejects spelling mistakes
    if set(p) - allowed:
        raise ValueError(f'Unknown presentation settings: {sorted(set(p) - allowed)}')
    if p['dpi'] not in (300, 600):
        raise ValueError('dpi must be 300 or 600')
    if p['tiff_compression'] not in ('LZW', 'None', 'PackBits'):
        raise ValueError('Unsupported TIFF compression')
    if set(p['required_formats']) != {'opju', 'png', 'pdf', 'tif'}:
        raise ValueError('This delivery contract requires OPJU, PNG, PDF and TIFF.')
    for key in ('page_width_mm', 'page_height_mm', 'font_size_pt'):
        if key in p and (not isinstance(p[key], (int, float)) or not 0 < p[key] <= 1000):
            raise ValueError(f'Invalid {key}')
    if ('page_width_mm' in p) != ('page_height_mm' in p):
        raise ValueError('Supply both page dimensions.')
    if 'font_family' in p:
        import re
        if not re.fullmatch(r'[\w .-]{1,100}', p['font_family']):
            raise ValueError('Invalid font family')
    return p


profile_defaults.extra = {'dpi', 'tiff_compression', 'required_formats', 'pdf_text_required',
                         'pdf_embedded_fonts_required', 'allow_full_page_raster', 'expected',
                         'page_width_mm', 'page_height_mm', 'font_family', 'font_size_pt'}


def prepare(backend, input_path, profile=None, original_sources=(), provenance=None, reuse=None):
    path = Path(input_path).resolve(strict=True)
    spec = read(path)
    def resolve(value):
        p = Path(value)
        return p if p.is_absolute() else path.parent / p
    files = [file_record(path, 'job' if backend == 'native' else 'plan')]
    if backend == 'native':
        import originpro_build as native
        native.validate_job(path, require_output=False)
        files.append(file_record(resolve(spec['data_csv']), 'plotted_source'))
        if spec.get('template_opju'):
            files.append(file_record(resolve(spec['template_opju']), 'template'))
        if spec['graph'].get('style_file'):
            files.append(file_record(resolve(spec['graph']['style_file']), 'style'))
            chosen_style = read(resolve(spec['graph']['style_file']))
            if chosen_style.get('curve_preset'):
                files.append(file_record(ROOT/'references'/Path(chosen_style['specification']).name, 'style_spec'))
        # All scientific fields are included by default; only known appearance/output fields are excluded.
        science = {k: v for k, v in spec.items() if k not in
                   {'data_csv', 'output_opju', 'qa_png', 'overwrite', 'template_opju', 'graph'}}
        graph = {k: v for k, v in spec['graph'].items() if k not in
                 {'series', 'style_file', 'long_name', 'legend', 'show_y_tick_labels'}}
        graph['series'] = [{k: v for k, v in s.items() if k not in {'color', 'line_width', 'line_style'}}
                           for s in spec['graph']['series']]
        science['graph'] = graph
        style = read(resolve(spec['graph']['style_file'])) if spec['graph'].get('style_file') else {}
        if spec.get('template_opju') and not style.get('curve_preset'):
            style = {}
        science['effective_defaults'] = {
            'reverse_x': spec['graph'].get('reverse_x', style.get('reverse_x', spec['graph'].get('spectrum_type','').lower()=='xps' if style.get('curve_preset') else False)),
            'y_padding_fraction': style.get('y_padding_fraction', 0),
            'x_label': spec['graph'].get('x_label', style.get('x_label', 'X')),
            'y_label': spec['graph'].get('y_label', style.get('y_label', 'Y'))}
    elif backend == 'routes':
        import originpro_routes as routes
        core = routes.load_core()
        core.bootstrap_engine(routes.ENGINE)
        core.validate_plan(spec)
        files.append(file_record(spec['source']['path'], 'plotted_source'))
        science = {'source': {k: v for k, v in spec['source'].items() if k != 'path'},
                   'figure_contract': spec['figure_contract'],
                   'template_id': spec['template']['id'],
                   'worker_mapping': spec['template'].get('worker_mapping'),
                   'display_transform': spec['template'].get('display_transform_or_profile')}
    else:
        raise ValueError('backend must be native or routes')
    files.extend(file_record(p, 'original_source') for p in original_sources)
    science['source_hashes'] = [{'role': f['role'], 'sha256': f['sha256']} for f in files
                                if f['role'] in ('plotted_source', 'original_source', 'template')]
    science['provenance'] = provenance or {'processing': 'No additional processing declared.'}
    presentation = {'profile': profile_defaults(profile), 'input': spec,
                    'template_and_style': [f for f in files if f['role'] in ('template', 'style')]}
    record = {'schema': SCHEMA, 'backend': backend, 'input': str(path), 'files': files,
              'science': science, 'science_sha256': digest(science),
              'presentation': presentation, 'presentation_sha256': digest(presentation),
              'engine': engine_record(), 'confirmation': None}
    if reuse:
        old = read(reuse) if isinstance(reuse, (str, Path)) else reuse
        check_seal(old)
        if old['science_sha256'] != record['science_sha256']:
            raise ValueError('Scientific content changed; previous data confirmation cannot be reused.')
        validate_confirmation(old)
        record['confirmation'] = copy.deepcopy(old['confirmation'])
    return seal(record)


def validate_confirmation(record):
    c = record.get('confirmation') or {}
    if c.get('science_sha256') != record['science_sha256'] or c.get('kind') not in ('user', 'test_fixture'):
        raise ValueError('Matching data confirmation is missing.')
    if not c.get('statement', '').strip() or not c.get('context', '').strip():
        raise ValueError('Confirmation requires the actual statement and its conversation/fixture context.')


def confirm(record, statement, context, kind='user'):
    validate(record, require_confirmation=False)
    record = copy.deepcopy(record)
    record['confirmation'] = {'science_sha256': record['science_sha256'], 'kind': kind,
                              'statement': statement, 'context': context,
                              'recorded_at': datetime.now(timezone.utc).isoformat()}
    validate_confirmation(record)
    return seal(record)


def validate(record, require_confirmation=True, check_engine=True):
    check_seal(record)
    if record.get('schema') != SCHEMA:
        raise ValueError('Unsupported delivery record schema')
    if digest(record['science']) != record['science_sha256'] or digest(record['presentation']) != record['presentation_sha256']:
        raise ValueError('Task digest mismatch')
    for f in record['files']:
        current = file_record(f['path'], f['role'])
        if current['sha256'] != f['sha256']:
            raise ValueError(f"Bound file changed ({f['role']}): {f['path']}")
    if check_engine and record['engine'] != engine_record():
        raise ValueError('Engine code changed; prepare a fresh record (reuse unchanged data confirmation).')
    if require_confirmation:
        validate_confirmation(record)
    return True
