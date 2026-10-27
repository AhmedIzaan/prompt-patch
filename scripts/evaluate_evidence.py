"""Generate formal measured results from actual saved Module 10/08 evidence."""
import argparse
import json
from pathlib import Path

from promptpatch.git_tool import GitEvidenceTool, RepositoryAccess
from promptpatch.repository import utc_now
from scripts.evaluation_support import snapshot, write


def load(path):
    return json.loads(Path(path).read_text())


def factual_audit(artifacts, live_db, demo_artifacts, git_repo):
    c2, c3 = (load(Path(demo_artifacts)/(name+'.json')) for name in ('cycle_2', 'cycle_3'))
    source = snapshot(live_db)
    write(artifacts/'live_source_evidence.json', {'read_at': utc_now(), 'mode': 'live-historical', 'database_snapshot': source})
    cases = {r['id']: r for r in source['test_cases']}
    executions = {r['id']: r for r in source['test_executions']}
    claims = []

    def claim(key, text, correct, refs, observed):
        claims.append({'claim_id': key, 'claim': text, 'correct': bool(correct), 'evidence_refs': refs, 'observed': observed})

    decimal = next(r for r in c2['executions'] if cases[r['test_case_id']]['case_key']=='T02')
    raw = json.loads(decimal['response']['raw_text'])
    case = cases[decimal['test_case_id']]
    claim('F01', 'Live v2 T02 extracted 4.5 mm, matching the approved source.',
          raw['estimated_settlement_mm'] == json.loads(case['expected_json'])['estimated_settlement_mm'] == 4.5
          and '4.5 mm' in case['input_text'] and decimal['status']=='pass'
          and json.loads(executions[decimal['id']]['response_json']) == decimal['response'],
          ['../demo/cycle_2.json#executions/'+decimal['id'], 'live_source_evidence.json#test_cases/'+case['id']],
          {'raw_response': decimal['response']['raw_text'], 'case': case})
    missing = next(r for r in c3['executions'] if cases[r['test_case_id']]['case_key']=='T05')
    raw, case = json.loads(missing['response']['raw_text']), cases[missing['test_case_id']]
    claim('F02', 'Live v3 T05 left the absent allowable limit null.',
          raw['allowable_settlement_mm'] is None and raw['evidence']['allowable'] is None
          and json.loads(case['expected_json'])['allowable_settlement_mm'] is None
          and 'No allowable settlement limit is specified' in case['input_text'] and missing['status']=='pass'
          and json.loads(executions[missing['id']]['response_json']) == missing['response'],
          ['../demo/cycle_3.json#executions/'+missing['id'], 'live_source_evidence.json#test_cases/'+case['id']],
          {'raw_response': missing['response']['raw_text'], 'source': case['input_text']})
    version = c3['prompt_version']
    tool = GitEvidenceTool(live_db, {'demo': RepositoryAccess(Path(git_repo), frozenset({version['prompt_path']}))})
    git = tool.read_git_prompt('demo', version['git_commit_sha'], version['prompt_path']).model_dump()
    write(artifacts/'git_claim_evidence.json', git)
    claim('F03', 'Successful v3 used registered Git snapshot 1fed5a700edb94ddff2568531ee3f80f76f42ddc.',
          git['commit_sha'] == version['git_commit_sha'] == '1fed5a700edb94ddff2568531ee3f80f76f42ddc'
          and git['content_hash'] == version['content_hash'],
          ['git_claim_evidence.json', '../demo/cycle_3.json#prompt_version'], {'registered': version, 'actual': git})
    decisions = [r for r in source['human_decisions'] if r['cycle_id']==c3['status']['cycle_id']]
    approval = decisions[0] if len(decisions)==1 else {}
    events = [r for r in source['audit_events'] if r['event_type']=='human_decision_recorded' and r['ref_id']==approval.get('id')]
    release = {'approval': approval, 'audit_events': events, 'cycle_id': c3['status']['cycle_id'],
               'prior_recommendation': c3['status']['recommendation'],
               'authorization': 'User explicitly granted prompt release approval in the Module 10 request on 2026-10-27.',
               'scope': 'Human acceptance of tested v3 only; no deployment/push. Historical exports retain their then-pending state.'}
    write(artifacts/'release_approval.json', release)
    claim('F04', 'Developer approved successful v3 separately from the agent recommendation.',
          approval.get('decision')=='approved' and approval.get('actor')=='developer'
          and approval.get('prompt_version_id')==version['id'] and len(events)==1
          and json.loads(events[0]['details_json']) == {'actor': 'developer', 'decision': 'approved'}
          and c3['status']['recommendation']['action']=='promote_candidate',
          ['release_approval.json', 'live_source_evidence.json#human_decisions/'+approval.get('id', 'missing')], release)
    risks = [r for r in source['failure_memories'] if r['project_id']=='demo']
    resolved = [r for r in source['audit_events'] if r['event_type']=='failure_resolved' and r['ref_id'] in {v['id'] for v in risks}]
    correct = len(risks)==3 and all(r['status']=='resolved' for r in risks)
    for risk in risks:
        matched = [e for e in resolved if e['ref_id']==risk['id'] and e['cycle_id']==risk['last_cycle_id']]
        execution = next((r for r in source['test_executions'] if r['id']==json.loads(risk['evidence_json']).get('execution_id')), None)
        correct = correct and len(matched)==1 and execution is not None and execution['status']=='pass'
    claim('F05', 'All three original demo risks resolved with passing execution and immutable resolution events.',
          correct, ['live_source_evidence.json#failure_memories', 'live_source_evidence.json#audit_events'],
          {'risks': risks, 'resolution_events': resolved})
    audit = {'sample_size': 5, 'correct_claims': sum(r['correct'] for r in claims), 'claims': claims,
             'method': 'Compare raw output/source, real Git blob, immutable human event and risk-resolution provenance; fictional domain.'}
    write(artifacts/'factual_claims.json', audit)
    return audit, approval


def build(artifacts, live_db, demo_artifacts, git_repo):
    artifacts = Path(artifacts)
    scenarios = load(artifacts/'scenarios.json')
    audit, approval = factual_audit(artifacts, live_db, demo_artifacts, git_repo)
    ablation_path = artifacts/'ablation/summary.json'
    ablation = load(ablation_path) if ablation_path.exists() else None
    retry = load(artifacts/'evidence/S07.json')
    representative_path = artifacts/'ablation/A01_memory_on.json'
    if representative_path.exists():
        representative = load(representative_path)
        measurement = {key: representative[key] for key in ('telemetry', 'wall_elapsed_ms', 'local_cpu_seconds', 'process_peak_rss_kib')}
        measurement['scope'] = 'Live A01 memory-on current review only. Conditioning excluded from cycle model counts; RSS cumulative process high water.'
        measurement['evidence_ref'] = 'ablation/A01_memory_on.json'
    else:
        measurement = {'telemetry': retry['telemetry'], 'scope': 'Offline S07 replay retry control, not live provider latency.',
                       'wall_elapsed_ms': retry['elapsed_ms'], 'local_cpu_seconds': retry['local_cpu_seconds'], 'evidence_ref': 'evidence/S07.json'}
    measurement['approximate_cost'] = None
    measurement['cost_note'] = 'No verified price used. Actual known token counters and measured local CPU/storage reported instead.'
    write(artifacts/'representative_run.json', measurement)
    total, passed = len(scenarios), sum(r['pass_fail']=='PASS' for r in scenarios)
    report = {'generated_at': utc_now(), 'passed_scenarios': passed, 'total_scenarios': total,
              'overall_pass_rate': passed/total if total else None, 'scenario_mode': 'offline-replay/control',
              'memory_on_successes': ablation['memory_on_successes'] if ablation else None,
              'memory_off_successes': ablation['memory_off_successes'] if ablation else None,
              'ablation_denominator': 3, 'ablation_status': 'executed' if ablation else 'NOT RUN',
              'attempted_pairs': ablation['attempted_pairs'] if ablation else 0,
              'completed_pairs_without_provider_error': ablation['completed_pairs_without_provider_error'] if ablation else 0,
              'ablation_mode': 'live current reviews, scripted conditioning history',
              'factual_claims_correct': audit['correct_claims'], 'factual_claims_sampled': 5,
              'retry_duplicate_actions': retry['duplicate_result_count_sql'],
              'retry_measurement_scope': 'S07 replay timeout injection; actual SQL over persisted results.',
              'failed_scenarios': [r['scenario_id'] for r in scenarios if r['pass_fail']=='FAIL'],
              'not_run_scenarios': [r['scenario_id'] for r in scenarios if r['pass_fail']=='NOT RUN'],
              'failed_ablation_requests': ablation['failed_requests'] if ablation else [],
              'failed_ablation_criteria': [{'comparison_id': p['comparison_id'], 'arm': arm}
                                          for p in (ablation or {}).get('pairs', []) for arm, value in p['arms'].items() if not value['success']],
              'historical_failure_examples': [
                  {'ref': '../demo/cycle_1.json', 'outcome': 'Real v1 T02/T06 extraction failures; revise.'},
                  {'ref': '../demo/cycle_3_observed_failure.json', 'outcome': 'Earlier v3 planner deadline failure; no extraction or successful review.'}],
              'teacher_approval': 'unverified', 'release_approval': approval.get('decision', 'unverified'),
              'statistical_significance_claimed': False,
              'limits': ['Ten scenarios measure controls with scripted provider, not live accuracy.',
                         'Three pairs are diagnostic; no statistical or broad superiority claim.',
                         'Conditioning history is scripted replay; current comparison model requests are live.',
                         'Source/diffs may independently identify regressions even without history.',
                         'Human rejection/open-risk enforcement remains active in both arms.',
                         'Costs unknown; one worker/cycle; no exactly-once remote billing guarantee.']}
    write(artifacts/'summary.json', report)
    lines = ['# Module 10 evaluation results', '',
             f"Measured scenarios: **{passed}/{total}** ({report['overall_pass_rate']:.0%}), explicitly offline replay/control.",
             f"Live comparisons: **{report['ablation_status']}**. Memory-on **{report['memory_on_successes']}/3**, memory-off **{report['memory_off_successes']}/3**.",
             f"Pairs attempted: {report['attempted_pairs']}; completed without provider errors: {report['completed_pairs_without_provider_error']}. Provider-limited arms remain in the denominator as unsuccessful, not evidence of reasoning failure.",
             'Conditioning histories are scripted. Diagnostic, not statistically significant.', '',
             '| Comparison | Arm | Actual selected IDs | Planner action | Recommendation | Criterion met | Provider error |',
             '|---|---|---|---|---|---|---|']
    for pair in (ablation or {}).get('pairs', []):
        for arm, value in pair['arms'].items():
            lines.append(f"| {pair['comparison_id']} | {arm} | {', '.join(value['selected_test_ids']) or 'none'} | {value['planner_action']} | {value['next_action']} | {value['success']} | {value['error'] or 'none'} |")
    lines += ['', 'Selection and execution are distinct. Each arm export lists executed IDs; a selected target blocked by a provider error does not meet the predeclared criterion. No planner response means no observed planner decision, even when the safe final action is needs_review.']
    lines += ['', f"Factual audit: **{audit['correct_claims']}/5** correct. Retry duplicate actions: **{report['retry_duplicate_actions']}**, measured from S07 SQLite.",
              '', 'Representative measurements: `representative_run.json`. Unknown token/cost values remain null. Local resource measurements are included.',
              '', 'Failures and limits:', '']
    lines += ['- '+text for text in report['limits']]
    lines += ['- Unmet ablation criteria: '+json.dumps(report['failed_ablation_criteria'])+'.',
              '- Failed ablation requests: '+json.dumps(report['failed_ablation_requests'])+'.',
              '- Earlier v1 extraction failures and v3 deadline failure remain linked in `summary.json`.',
              '- Teacher approval unverified. Actual v3 release approval saved separately in `release_approval.json`.',
              '', 'Evidence: [scenarios](scenarios.json), [CSV](scenarios.csv), [predeclared protocol](ablation/protocol.json), [five-claim audit](factual_claims.json).',
              '', 'See `docs/TEST_SCENARIOS.md` for commands. Exact requests/responses and source IDs remain in exports. No Module 11 report/submission package generated.']
    (artifacts/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, default=Path('artifacts/evaluation'))
    parser.add_argument('--live-db', type=Path, default=Path('data/module08/live/memory.sqlite3'))
    parser.add_argument('--demo-artifacts', type=Path, default=Path('artifacts/demo'))
    parser.add_argument('--git-repo', type=Path, default=Path('samples/demo_git_repo'))
    args = parser.parse_args(argv)
    result = build(args.artifacts, args.live_db, args.demo_artifacts, args.git_repo)
    print(json.dumps(result, indent=2))
    return 0 if result['passed_scenarios']==10 and result['factual_claims_correct']==5 and result['ablation_status']=='executed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
