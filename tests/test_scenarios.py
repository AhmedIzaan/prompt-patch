"""Formal scenarios use actual SQLite/Git/graph, explicitly handwritten replay."""
import copy
import csv
import json
from pathlib import Path

import pytest

from scripts.evaluation_support import Workspace, FixtureProvider, fresh_directory, snapshot
from scripts.run_scenarios import COLUMNS, DESCRIPTIONS, run, scenario
from scripts.run_ablation import EXPECTATIONS, compare_inputs, prepare, selected_success


@pytest.mark.parametrize('scenario_id', DESCRIPTIONS)
def test_formal_scenario(tmp_path, scenario_id):
    result = scenario(Workspace(tmp_path/scenario_id), scenario_id)
    assert result['mode'] == 'offline-replay' and result['live_inference'] is False
    assert result['summary'] and result['database_snapshot']['audit_events']


def test_scenario_exports_and_pass_rate_are_measured(tmp_path):
    artifacts = tmp_path/'artifacts'
    artifacts.mkdir()
    result = run(tmp_path/'runtime', artifacts)
    assert result['passed_scenarios'] == result['total_scenarios'] == 10
    rows = json.loads((artifacts/'scenarios.json').read_text())
    with (artifacts/'scenarios.csv').open(newline='') as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(csv_rows) == len(rows) == 10
    assert tuple(rows[0]) == COLUMNS
    assert [row['scenario_id'] for row in csv_rows] == list(DESCRIPTIONS)
    for row in rows:
        assert all((artifacts/ref).is_file() for ref in row['evidence_refs'])


def test_scenario_failure_is_exported_not_recast_as_pass(tmp_path, monkeypatch):
    import scripts.run_scenarios as module
    original = module.scenario
    def broken(w, key):
        if key == 'S01':
            raise AssertionError('Injected test failure')
        return original(w, key)
    monkeypatch.setattr(module, 'scenario', broken)
    artifacts = tmp_path/'artifacts'; artifacts.mkdir()
    summary = module.run(tmp_path/'runtime', artifacts)
    assert summary['passed_scenarios'] == 9 and summary['failed_scenarios'] == ['S01']
    assert json.loads((artifacts/'scenarios.json').read_text())[0]['pass_fail'] == 'FAIL'


def test_ablation_protocol_precedes_calls_and_clones_are_identical(tmp_path):
    artifacts, runtime = tmp_path/'artifacts', tmp_path/'runtime'
    manifest = prepare(runtime, artifacts, 'offline-no-call')
    protocol = json.loads((artifacts/'protocol.json').read_text())
    assert len(protocol['comparisons']) == 3 and protocol['settings']['temperature'] == 0
    assert protocol['settings']['seed'] is None
    for pair in manifest['pairs'].values():
        left, right = pair['arms']['memory_on'], pair['arms']['memory_off']
        assert Path(left['db']).read_bytes() == Path(right['db']).read_bytes()
        assert left['sha256_before_run'] == right['sha256_before_run']
        assert not Path(left['checkpoint']).exists() and not Path(right['checkpoint']).exists()
    assert not (artifacts/'summary.json').exists()  # No live inference invented at preparation.
    with pytest.raises(ValueError):
        prepare(runtime, artifacts, 'offline-no-call')


def test_success_metric_does_not_force_difference_or_confuse_safety_with_memory():
    for expectation in EXPECTATIONS[:2]:
        result = {'plan': {'decision': 'RUN_TESTS', 'test_ids': ['T01', expectation['relevant_test']]},
                  'executed_test_ids': ['T01', expectation['relevant_test']], 'error': None}
        assert selected_success(expectation, result)
        assert not selected_success(expectation, {**result, 'executed_test_ids': []})
        assert not selected_success(expectation, {**result, 'error': 'timeout'})
    result = {'plan': {'decision': 'RUN_TESTS', 'test_ids': ['T01']}, 'next_action': 'needs_review', 'executed_test_ids': ['T01']}
    assert not selected_success(EXPECTATIONS[2], result)
    assert selected_success(EXPECTATIONS[2], {'plan': {'decision': 'HOLD_FOR_APPROVAL'}, 'executed_test_ids': []})


def test_equivalence_guard_detects_changed_current_policy():
    schema = {'properties': {'memory_evidence_ids': {'maxItems': 0}, 'decision': {'type': 'string'}}}
    request = {'input': {'policy': {'id': 'same'}, 'long_term_memory': {'source_refs': ['risk:x']}},
               'settings': {'temperature': 0}, 'system_instruction': 'same', 'response_schema': schema,
               'supplied_memory_refs': ['risk:x']}
    on = {'exact_planner_request_and_response': copy.deepcopy(request)}
    off = copy.deepcopy(on)
    off['exact_planner_request_and_response']['input']['long_term_memory'] = None
    off['exact_planner_request_and_response']['supplied_memory_refs'] = []
    assert compare_inputs(on, off)['same_current_input']
    off['exact_planner_request_and_response']['input']['policy']['id'] = 'changed'
    with pytest.raises(AssertionError):
        compare_inputs(on, off)


def test_existing_evidence_directories_are_protected(tmp_path):
    root = fresh_directory(tmp_path/'owned')
    (root/'result.json').write_text('{}')
    with pytest.raises(ValueError):
        fresh_directory(root)


def test_actual_paired_contexts_match_and_rejection_guard_is_not_ablated(tmp_path):
    from promptpatch.model_provider import ModelSettings
    manifest = prepare(tmp_path/'runtime', tmp_path/'artifacts', 'offline-no-call')
    pair = manifest['pairs']['A03']
    results = {}
    for arm in ('memory_on', 'memory_off'):
        w = Workspace(Path(pair['arms'][arm]['db']).parent, seed=False)
        w.repo = Path(pair['repo'])
        provider = FixtureProvider(w.cases(), ['T01'])
        state = w.graph(provider, ModelSettings(model_id='offline-no-call')).run(
            'demo', pair['cycle_id'], memory_enabled=arm=='memory_on', base_version_id=pair['base_version_id'])
        record = next(r for r in snapshot(w.db)['planner_decisions'] if r['cycle_id']==pair['cycle_id'])
        results[arm] = {'exact_planner_request_and_response': json.loads(record['decision_json'])}
        assert state['recommendation']['prior_rejection'] and state['next_action']=='needs_review'
        assert len(state['execution_results'])==1
    assert compare_inputs(results['memory_on'], results['memory_off'])['same_current_input']
