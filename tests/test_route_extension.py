"""Exercise real data preparation and plan validation without starting Origin."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import originpro_routes as routes

core = routes.load_core()
core.bootstrap_engine(routes.ENGINE)
from origin_sciplot.template_registry import TemplateRegistry

MANIFESTS = TemplateRegistry().implemented()


def test_all_public_routes_and_vendor_integrity():
    assert len(MANIFESTS) == 40
    assert {m.id for m in MANIFESTS} == core.VERIFIED_TEMPLATE_IDS
    assert routes.check_install()['ok']


@pytest.mark.parametrize('manifest', MANIFESTS, ids=lambda m: m.id)
def test_bundled_example_builds_an_executable_plan_without_changing_data(manifest):
    source = manifest.example_path
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    understanding = core.understand_data(source, template_id=manifest.id, engine_home=routes.ENGINE)
    assert understanding['execution']['origin_called'] is False
    assert understanding['confirmation_gate']['can_confirm_now']
    # This is explicit test-fixture consent for bundled synthetic teaching data only.
    consent = understanding['confirmation_gate']['confirmation_payload_template']
    plan = core.build_plan(source, template_id=manifest.id, claim='Synthetic integration fixture',
                           evidence_role='validation', semantic_confirmation=consent,
                           engine_home=routes.ENGINE)
    core.validate_plan(plan)
    command, env, engine = core.build_worker_command(plan, engine_home=routes.ENGINE,
                                                    python_executable=sys.executable, close_origin=True)
    assert command[command.index('--template-id') + 1] == plan['template']['id']
    assert engine == routes.ENGINE
    assert Path(env['PYTHONPATH'].split(__import__('os').pathsep)[0]).is_dir()
    assert plan['source']['sha256'] == before
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_missing_confirmation_is_rejected():
    manifest = next(m for m in MANIFESTS if m.id == 'bar')
    with pytest.raises(core.EditaPlotError, match='confirm|Confirm'):
        core.build_plan(manifest.example_path, template_id='bar', claim='Synthetic fixture',
                        evidence_role='validation', engine_home=routes.ENGINE)


def test_changed_source_invalidates_saved_plan(tmp_path):
    manifest = next(m for m in MANIFESTS if m.id == 'bar')
    source = tmp_path / 'synthetic.csv'
    source.write_bytes(manifest.example_path.read_bytes())
    u = core.understand_data(source, template_id='bar', engine_home=routes.ENGINE)
    plan = core.build_plan(source, template_id='bar', claim='Synthetic fixture',
                          evidence_role='validation', engine_home=routes.ENGINE,
                          semantic_confirmation=u['confirmation_gate']['confirmation_payload_template'])
    saved = tmp_path / 'plan.json'
    saved.write_text(json.dumps(plan), encoding='utf-8')
    cli = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'scripts/originpro_routes.py'),
                          'validate-plan', str(saved)], capture_output=True, text=True,
                         encoding='utf-8', timeout=30)
    assert cli.returncode == 0, cli.stdout + cli.stderr
    assert routes.main(['validate-plan', str(saved)]) == 0
    source.write_bytes(source.read_bytes() + b'\n')
    with pytest.raises(core.EditaPlotError, match='source file changed'):
        routes.main(['validate-plan', str(saved)])


def test_calibration_counts_require_helper_approval_and_are_not_a_curve():
    manifest = next(m for m in MANIFESTS if m.id == 'calibration_curve')
    u = core.understand_data(manifest.example_path, template_id=manifest.id, engine_home=routes.ENGINE)
    items = u['understanding']['column_decisions']
    count = next(i for i in items if i['semantic_role'] == 'count')
    assert count['disposition'] == 'support_only'
    for element in u['understanding']['figure_elements']:
        assert count['item_id'] not in element['data_item_ids']
    helper = u['understanding']['derived_items'][0]
    assert helper['input_item_ids'] == [count['item_id']]
    assert helper['parameters']['factor'] == pytest.approx(0.12 / 164)
    consent = dict(u['confirmation_gate']['confirmation_payload_template'])
    consent['approved_derived_item_ids'] = []
    with pytest.raises(core.EditaPlotError):
        core.build_plan(manifest.example_path, template_id=manifest.id, claim='Synthetic fixture',
                        evidence_role='validation', semantic_confirmation=consent,
                        engine_home=routes.ENGINE)


def test_empty_architecture_requires_real_discovery(monkeypatch):
    monkeypatch.setattr(core.platform, 'machine', lambda: '')
    monkeypatch.setattr(core, '_native_windows_machine', lambda: 'AMD64')
    assert core.windows_host_compatibility(system='Windows', windows_major=10)['compatible']
    monkeypatch.setattr(core, '_native_windows_machine', lambda: 'ARM64')
    assert not core.windows_host_compatibility(system='Windows', windows_major=10)['compatible']
    monkeypatch.setattr(core, '_native_windows_machine', lambda: '')
    assert not core.windows_host_compatibility(system='Windows', windows_major=10)['compatible']
