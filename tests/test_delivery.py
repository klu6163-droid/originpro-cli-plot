"""Regression gates for stale approval, saved-state changes and broken deliverables."""
import copy
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import delivery_contract as dc
from origin_readback import compare
from originpro_delivery import verify


@pytest.fixture
def task(tmp_path):
    data = tmp_path/'data.csv'
    data.write_text('x,y,z\n1,3,5\n2,4,6\n', encoding='utf-8')
    style = tmp_path/'style.json'
    dc.write(style, {})
    job = tmp_path/'job.json'
    dc.write(job, {'data_csv': str(data), 'output_opju': str(tmp_path/'result.opju'),
                   'worksheet': {'columns': [{'field': n, 'units': 'eV' if n == 'x' else 'a.u.'} for n in ['x','y','z']]},
                   'graph': {'x_column': 0, 'series': [{'y_column': 1}], 'style_file': str(style)}})
    record = dc.prepare('native', job)
    record = dc.confirm(record, 'Use this synthetic test mapping.', 'pytest fixture', 'test_fixture')
    return job, data, record


def test_unconfirmed_job_cannot_execute(task):
    job, _, _ = task
    with pytest.raises(ValueError, match='confirmation'):
        dc.validate(dc.prepare('native', job))


def test_changed_data_fails_even_at_same_path(task):
    _, data, record = task
    data.write_text(data.read_text()+'3,7,8\n')
    with pytest.raises(ValueError, match='Bound file changed'):
        dc.validate(record)


def test_mapping_change_requires_new_confirmation(task):
    job, _, record = task
    spec = dc.read(job)
    spec['graph']['series'][0]['y_column'] = 2
    dc.write(job, spec)
    with pytest.raises(ValueError, match='Scientific content changed'):
        dc.prepare('native', job, reuse=record)


def test_color_font_dpi_changes_reuse_science_confirmation(task):
    job, _, record = task
    spec = dc.read(job)
    spec['graph']['series'][0]['color'] = '#ff0000'
    dc.write(job, spec)
    fresh = dc.prepare('native', job, {'dpi': 600, 'font_family': 'Arial'}, reuse=record)
    assert fresh['science_sha256'] == record['science_sha256']
    assert fresh['presentation_sha256'] != record['presentation_sha256']
    assert fresh['confirmation'] == record['confirmation']
    assert dc.validate(fresh)


def test_original_source_change_is_bound(task, tmp_path):
    job, _, _ = task
    raw = tmp_path/'acquisition.txt'
    raw.write_text('original measured data')
    record = dc.prepare('native', job, original_sources=[raw], provenance={'sheet': 'Data', 'processing': 'lossless CSV export'})
    record = dc.confirm(record, 'Test original data binding', 'pytest', 'test_fixture')
    raw.write_text('other data')
    with pytest.raises(ValueError, match='original_source'):
        dc.validate(record)


def test_style_template_change_does_not_silently_pass(task):
    job, _, record = task
    dc.write(dc.read(job)['graph']['style_file'], {'font_family': 'Other'})
    with pytest.raises(ValueError, match='style'):
        dc.validate(record)


def test_confirmation_and_record_tampering_is_rejected(task):
    _, _, record = task
    record['confirmation']['statement'] = 'forged replacement'
    with pytest.raises(ValueError, match='record changed'):
        dc.validate(record)


def test_style_default_axis_direction_is_scientific(task):
    job, _, record = task
    dc.write(dc.read(job)['graph']['style_file'], {'reverse_x': True})
    with pytest.raises(ValueError, match='Scientific content changed'):
        dc.prepare('native', job, reuse=record)


def test_template_may_contain_retained_data_and_is_science_bound(task, tmp_path):
    job, _, _ = task
    template = tmp_path/'template.opju'; template.write_bytes(b'synthetic-template-data-v1')
    spec = dc.read(job); spec['template_opju'] = str(template); dc.write(job, spec)
    record = dc.confirm(dc.prepare('native',job), 'Synthetic template', 'pytest', 'test_fixture')
    template.write_bytes(b'synthetic-template-data-v2')
    with pytest.raises(ValueError, match='Scientific content changed'):
        dc.prepare('native',job,reuse=record)


def test_font_reset_layer_loss_and_data_rebinding_fail():
    before = {'g1/layer_count': 2, 'g1/l2/axis/y2/label.font': 76,
              'g1/l1/text/XB/font': 76, 'g1/l1/p1/y_range': '[Book1]1!B', 'w1/s1/data_sha256': 'abc'}
    for key, replacement in [('g1/layer_count',1), ('g1/l2/axis/y2/label.font',1),
                             ('g1/l1/text/XB/font', 32), ('g1/l1/p1/y_range','[Book1]1!C'),
                             ('w1/s1/data_sha256','changed')]:
        after = dict(before, **{key: replacement})
        report = compare(before, after)
        assert not report['pass']
        assert any(r['property'] == key and not r['pass'] for r in report['checks'])


def test_missing_required_export_invalidates_previous_pass(task, tmp_path):
    _, _, record = task
    dc.write(tmp_path/'task-record.json', record)
    pdf = tmp_path/'result.pdf'
    pdf.write_bytes(b'%PDF-test')
    manifest = dc.seal({'programmatic_pass': True, 'artifacts': [dc.file_record(pdf, 'pdf')]})
    dc.write(tmp_path/'delivery-manifest.json', manifest)
    assert verify(tmp_path)['programmatic_pass']
    assert not verify(tmp_path)['complete']
    pdf.unlink()
    assert not verify(tmp_path)['programmatic_pass']


def test_visual_review_cannot_survive_changed_output(task, tmp_path):
    _, _, record = task
    dc.write(tmp_path/'task-record.json', record)
    png = tmp_path/'result.png'; png.write_bytes(b'first')
    manifest = dc.seal({'programmatic_pass': True, 'artifacts': [dc.file_record(png,'png')]})
    dc.write(tmp_path/'delivery-manifest.json', manifest)
    dc.write(tmp_path/'visual-review.json', dc.seal({'pass': True, 'manifest_sha256': manifest['record_sha256']}))
    assert verify(tmp_path)['complete']
    png.write_bytes(b'second')
    assert not verify(tmp_path)['complete']
