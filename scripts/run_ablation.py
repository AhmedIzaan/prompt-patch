"""Prepare three paired snapshots, then run six actual live reviews; no replay fallback."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import resource
from time import perf_counter

from promptpatch.approvals import decide_version, propose_policy, approve_policy
from promptpatch.config import load_settings
from promptpatch.model_provider import GeminiProvider, ModelSettings
from promptpatch.repository import digest, utc_now
from promptpatch.telemetry import review_telemetry
from scripts.evaluation_support import Workspace, backup, fresh_directory, snapshot, write
from scripts.seed_demo import SAMPLES

EXPECTATIONS = [
    {'comparison_id': 'A01', 'version': 'v2', 'base_version': 'v1', 'relevant_test': 'T02',
     'starting_state': 'One scripted v1 decimal failure; T02 open; no later history.',
     'expected_difference': 'Memory-on prioritizes T02 with historical citation; memory-off may use its discretionary slots elsewhere.',
     'success_rule': 'Valid RUN_TESTS selects T02 and actually executes it; no requirement that its extraction passes.',
     'order': ['memory_on', 'memory_off']},
    {'comparison_id': 'A02', 'version': 'v3', 'base_version': 'v2', 'relevant_test': 'T05',
     'starting_state': 'Scripted v1 decimal failure resolved by v2; newly scripted absent-limit T05 failure open.',
     'expected_difference': 'Memory-on prioritizes T05 with historical citation; memory-off may miss the exact prior regression.',
     'success_rule': 'Valid RUN_TESTS selects T05 and actually executes it; no requirement that its extraction passes.',
     'order': ['memory_off', 'memory_on']},
    {'comparison_id': 'A03', 'version': 'v3', 'base_version': 'v2', 'relevant_test': None,
     'starting_state': 'Prior scripted failures resolved by v3; fixture owner approved policy 2 then explicitly rejected v3 pending clarification.',
     'expected_difference': 'Memory-on may HOLD_FOR_APPROVAL or REQUEST_CLARIFICATION citing rejection; memory-off may RUN_TESTS. Both retain mandatory human rejection protection.',
     'success_rule': 'Valid planner HOLD_FOR_APPROVAL or REQUEST_CLARIFICATION; no extraction calls. A deterministic needs_review recommendation alone is not a memory success.',
     'order': ['memory_on', 'memory_off']},
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def selected_success(expectation, result):
    plan = result.get('plan') or {}
    if result.get('error'):
        return False
    if expectation['relevant_test']:
        return (plan.get('decision') == 'RUN_TESTS' and expectation['relevant_test'] in plan.get('test_ids', [])
                and expectation['relevant_test'] in result.get('executed_test_ids', []))
    return plan.get('decision') in {'HOLD_FOR_APPROVAL', 'REQUEST_CLARIFICATION'} and not result.get('executed_test_ids')


def prepare(runtime, artifacts, model):
    runtime, artifacts = fresh_directory(runtime), fresh_directory(artifacts)
    settings = ModelSettings(model_id=model, temperature=0.0, seed=None, timeout_ms=30000, max_attempts=2)
    # Frozen before ANY live comparison request. Histories below are explicit fixtures.
    protocol = {'protocol_version': 1, 'defined_at': utc_now(), 'mode': 'live',
                'history_provenance': 'Handwritten replay conditioning generated through real graph/store; not previous live inference.',
                'comparisons': copy.deepcopy(EXPECTATIONS), 'settings': settings.model_dump(),
                'only_intervention': 'Hide long_term_memory from planner; citation schema follows available history. Current source/catalog/policy/settings identical.',
                'safety_boundary': 'Memory-off still enforces authoritative open-risk and human rejection constraints after execution.',
                'limit': 'Six new reviews; at most 4 extractions per review, at most 2 attempts per extraction; one planner attempt per review.',
                'interpretation': 'Three diagnostic pairs, not statistical proof; provider may vary even at temperature zero.'}
    write(artifacts/'protocol.json', protocol)
    manifest = {'runtime': str(runtime), 'protocol_sha256': sha(artifacts/'protocol.json'), 'pairs': {}}
    for expected in EXPECTATIONS:
        name = expected['comparison_id']
        w = Workspace(runtime/name/'baseline')
        w.run('history-decimal', ['T01', 'T02'], version='v1', wrong={'T02': {'estimated_settlement_mm': 5.0}})
        if name in {'A02', 'A03'}:
            w.run('history-missing', ['T01', 'T02', 'T05'], version='v2', wrong={'T05': {'allowable_settlement_mm': 0.0}})
        if name == 'A03':
            propose_policy(w.db, 'demo', SAMPLES/'evaluation_policy_v2.json', actor='module10-fixture-owner',
                           reason='Synthetic approved correction conditioning, separate from real user approval.')
            approve_policy(w.db, 'demo', 2, actor='module10-fixture-owner')
            w.run('history-fixed', ['T01', 'T02', 'T05'], version='v3')
            decide_version(w.db, 'demo', 'v3', 'history-fixed', 'rejected', actor='module10-fixture-owner',
                           comments='Synthetic rejection pending developer clarification of scope. Further passing tests alone do not resolve the decision.')
        cycle = w.cycle('ablation-'+name, expected['version'])
        start = snapshot(w.db)
        write(artifacts/(name+'_starting_state.json'), {'mode': 'scripted-conditioning', 'database_snapshot': start})
        clones = {}
        for arm in ('memory_on', 'memory_off'):
            clone = Workspace(runtime/name/arm, seed=False)
            backup(w.db, clone.db)
            clones[arm] = {'db': str(clone.db), 'checkpoint': str(clone.checkpoint), 'sha256_before_run': sha(clone.db)}
        assert clones['memory_on']['sha256_before_run'] == clones['memory_off']['sha256_before_run']
        manifest['pairs'][name] = {'cycle_id': cycle['id'], 'repo': str(w.repo),
                                  'base_version_id': w.versions()[expected['base_version']]['id'],
                                  'arms': clones, 'starting_state_digest': digest(start)}
    write(artifacts/'manifest.json', manifest)
    return manifest


def arm_result(db, cycle_id, state, elapsed, cpu, checkpoint):
    saved = snapshot(db)
    row = next(r for r in saved['planner_decisions'] if r['cycle_id'] == cycle_id)
    planner = json.loads(row['decision_json'])
    return {'mode': 'live', 'history_mode': 'scripted-conditioning', 'generated_at': utc_now(),
            'state': state, 'plan': planner['plan'], 'error': state.get('error') or planner.get('error'),
            'executed_test_ids': [r['test_id'] for r in state.get('execution_results', [])],
            'next_action': state['next_action'], 'planner_record': row, 'exact_planner_request_and_response': planner,
            'database_snapshot': saved, 'wall_elapsed_ms': elapsed, 'local_cpu_seconds': cpu,
            'process_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'telemetry': review_telemetry(db, 'demo', cycle_id, checkpoint_path=checkpoint)}


def compare_inputs(left, right):
    a = copy.deepcopy(left['exact_planner_request_and_response'])
    b = copy.deepcopy(right['exact_planner_request_and_response'])
    history_on = a['input'].pop('long_term_memory')
    history_off = b['input'].pop('long_term_memory')
    assert history_on is not None and history_off is None
    assert a['input'] == b['input'] and a['settings'] == b['settings'] and a['system_instruction'] == b['system_instruction']
    a['response_schema']['properties'].pop('memory_evidence_ids')
    b['response_schema']['properties'].pop('memory_evidence_ids')
    assert a['response_schema'] == b['response_schema']
    return {'same_current_input': True, 'same_settings_and_instruction': True,
            'same_schema_except_history_citation_boundary': True, 'memory_on_refs': left['exact_planner_request_and_response']['supplied_memory_refs'],
            'memory_off_refs': right['exact_planner_request_and_response']['supplied_memory_refs']}


def run(artifacts):
    artifacts = Path(artifacts).resolve()
    protocol = json.loads((artifacts/'protocol.json').read_text())
    manifest = json.loads((artifacts/'manifest.json').read_text())
    if sha(artifacts/'protocol.json') != manifest['protocol_sha256']:
        raise ValueError('Frozen protocol changed; use new preparation directories.')
    settings = load_settings()
    if settings.mode != 'live' or not settings.gemini_api_key:
        raise ValueError('Live mode and GEMINI_API_KEY required; no replay fallback.')
    model = ModelSettings.model_validate(protocol['settings'])
    if settings.gemini_model != model.model_id:
        raise ValueError('Configured model must match the predeclared protocol model.')
    pairs = []
    for expected in protocol['comparisons']:
        name = expected['comparison_id']
        info, results = manifest['pairs'][name], {}
        for arm in expected['order']:
            output = artifacts/(name+'_'+arm+'.json')
            if output.exists():
                results[arm] = json.loads(output.read_text())
                if results[arm]['protocol_sha256'] != manifest['protocol_sha256']:
                    raise ValueError('Saved arm belongs to a different protocol.')
                continue  # Never resample a recorded result, even a failed request.
            paths = info['arms'][arm]
            if sha(paths['db']) != paths['sha256_before_run']:
                raise ValueError('Arm DB changed without an exported result; inspect interruption instead of resampling.')
            w = Workspace(Path(paths['db']).parent, seed=False)
            w.repo = Path(info['repo'])
            provider = GeminiProvider(settings.gemini_api_key)
            before = resource.getrusage(resource.RUSAGE_SELF)
            start = perf_counter()
            state = w.graph(provider, model).run('demo', info['cycle_id'], memory_enabled=arm=='memory_on',
                                                 base_version_id=info['base_version_id'])
            elapsed = (perf_counter()-start)*1000
            after = resource.getrusage(resource.RUSAGE_SELF)
            results[arm] = arm_result(w.db, info['cycle_id'], state, elapsed,
                                      after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime, w.checkpoint)
            results[arm]['protocol_sha256'] = manifest['protocol_sha256']
            results[arm]['relevant_selection_success'] = selected_success(expected, results[arm])
            write(output, results[arm])
            print(json.dumps({'comparison': name, 'arm': arm, 'selected': state['selected_test_ids'],
                              'next_action': state['next_action'], 'error': state.get('error')}), flush=True)
        checks = compare_inputs(results['memory_on'], results['memory_off'])
        pairs.append({'comparison_id': name, 'expected_difference': expected['expected_difference'],
                      'comparison_status': 'provider_limited' if any(value['error'] for value in results.values()) else 'completed',
                      'input_equivalence': checks, 'arms': {arm: {
                          'selected_test_ids': (value['plan'] or {}).get('test_ids', []),
                          'planner_action': (value['plan'] or {}).get('decision'),
                          'next_action': value['next_action'], 'error': value['error'],
                          'relevant_test_selected_by_planner': expected['relevant_test'] in (value['plan'] or {}).get('test_ids', []) if expected['relevant_test'] else None,
                          'executed_test_ids': value['executed_test_ids'],
                          'memory_citations': (value['plan'] or {}).get('memory_evidence_ids', []),
                          'success': value['relevant_selection_success'],
                          'evidence_ref': name+'_'+arm+'.json'} for arm, value in results.items()}})
    summary = {'mode': 'live', 'conditioning_history': 'scripted, not live', 'pairs': pairs,
               'memory_on_successes': sum(p['arms']['memory_on']['success'] for p in pairs),
               'memory_off_successes': sum(p['arms']['memory_off']['success'] for p in pairs), 'denominator': 3,
               'attempted_pairs': len(pairs), 'completed_pairs_without_provider_error': sum(p['comparison_status']=='completed' for p in pairs),
               'failed_requests': [{'comparison_id': p['comparison_id'], 'arm': arm, 'error': value['error']}
                                   for p in pairs for arm, value in p['arms'].items() if value['error']],
               'statistically_significant': False, 'approximate_cost': None,
               'notes': ['No forced choices by memory flag; six actual graph runs using GeminiProvider.',
                         'A03 scores planner restraint, not mandatory rejection enforcement, which is identical in both arms.',
                         'With only three pairs, success does not establish general effectiveness. Exact same input may still vary.']}
    write(artifacts/'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'pairs'}, indent=2))
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--runtime', type=Path, default=Path('data/module10/ablation'))
    prep.add_argument('--artifacts', type=Path, default=Path('artifacts/evaluation/ablation'))
    prep.add_argument('--model', required=True)
    live = sub.add_parser('run')
    live.add_argument('--artifacts', type=Path, default=Path('artifacts/evaluation/ablation'))
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        prepare(args.runtime, args.artifacts, args.model)
        print('Protocol frozen; paired snapshots prepared. No live requests made.')
    else:
        run(args.artifacts)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
