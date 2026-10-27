"""Verify final local deliverables/evidence; never package, upload or call a model."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import xml.etree.ElementTree as ET

from promptpatch.repository import utc_now
from promptpatch.security import GOOGLE_KEY
from scripts.evaluation_support import write

ROOT = Path(__file__).resolve().parents[1]
DOCS = ('IMPLEMENTATION_STATUS.md','MEMORY_SCHEMA.md','ARCHITECTURE.md','TEST_SCENARIOS.md',
        'EVALUATION_RESULTS.md','TECHNICAL_REPORT.md','DEMO_SCRIPT.md','SUBMISSION_CHECKLIST.md','REQUIREMENT_TRACEABILITY.md')


def verify(artifacts, junit, *, secret_values=()):
    artifacts, junit = Path(artifacts), Path(junit)
    required = [ROOT/'README.md', ROOT/'pyproject.toml', ROOT/'requirements-dev.txt', ROOT/'config/.env.example']
    required += [ROOT/'docs'/name for name in DOCS]
    required += [artifacts/name for name in ('clean_environment.json','ui_http.json','ui_recorded_demo.json',
                 'demo_replay/summary.json','demo_replay/process_evidence.json',
                 'scenarios/scenarios.json','scenarios/scenarios.csv','scenarios/scenario_summary.json')]
    assert all(p.is_file() for p in required), 'A required final deliverable is missing.'
    assert re.search(r'^GEMINI_API_KEY=\s*$', (ROOT/'config/.env.example').read_text(), re.M)
    report = (ROOT/'docs/TECHNICAL_REPORT.md').read_text()
    assert report.count('page-break-after')==4 and len(re.findall(r'^## Page ',report,re.M))==5
    report_words = len(re.findall(r'\b[\w-]+\b',report))
    cases = list(ET.parse(junit).iter('testcase'))
    failed = sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
    skipped = sum(c.find('skipped') is not None for c in cases)
    assert cases and failed==skipped==0, 'Final tests must actually pass without skips.'
    scenarios = json.loads((artifacts/'scenarios/scenarios.json').read_text())
    assert len(scenarios)==len({r['scenario_id'] for r in scenarios})==10
    assert all(r['pass_fail']=='PASS' for r in scenarios)
    for row in scenarios:
        assert all((artifacts/'scenarios'/ref).is_file() for ref in row['evidence_refs'])
    demo = json.loads((artifacts/'demo_replay/summary.json').read_text())
    assert demo['mode']=='replay' and demo['live_inference'] is False
    assert demo['process_restart_verified'] and demo['sources_and_import_events_unchanged']
    assert [c['recommendation'] for c in demo['cycles']]==['revise','revise','promote_candidate']
    clean = json.loads((artifacts/'clean_environment.json').read_text())
    assert clean['live_model_calls']==0 and all(r['exit_code']==0 for r in clean['commands'])
    http = json.loads((artifacts/'ui_http.json').read_text())
    assert all(c['status']==200 and c['body_ok'] for c in http['checks'])
    recorded = json.loads((artifacts/'ui_recorded_demo.json').read_text())
    assert recorded['db_counts_before']==recorded['db_counts_after'] and recorded['metrics']['Human decision']=='Approved'
    original = json.loads((ROOT/'artifacts/evaluation/summary.json').read_text())
    assert original['memory_on_successes']==original['memory_off_successes']==1
    assert original['completed_pairs_without_provider_error']==1 and len(original['failed_ablation_requests'])==2
    checks=[]
    for p in (ROOT/'data/module11').rglob('*.sqlite3'):
        with sqlite3.connect(p) as conn:
            integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
            fks=list(conn.execute('PRAGMA foreign_key_check'))
            assert integrity=='ok' and not fks
        checks.append({'path':str(p.relative_to(ROOT)),'integrity':integrity,'foreign_key_errors':len(fks)})
    paths = [p for base in (artifacts,ROOT/'src',ROOT/'scripts',ROOT/'docs',ROOT/'config')
             for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [ROOT/'README.md',junit]
    paths += [p for p in (ROOT/'data/module11').rglob('*') if p.is_file()]
    for p in paths:
        content = p.read_bytes()
        assert not any(value.encode() in content for value in secret_values if value), 'Credential scan failed; value suppressed.'
    assert not any(GOOGLE_KEY.search(p.read_text()) for p in required if p.suffix in {'.json','.md','.example'})
    links=[]
    for p in [ROOT/'README.md',*[ROOT/'docs'/name for name in DOCS]]:
        for target in re.findall(r'\]\(([^\s)]+)\)',p.read_text()):
            if '://' not in target and not target.startswith('#'):
                relative=target.split('#',1)[0]
                assert (p.parent/relative).exists(), 'Broken local documentation link: '+relative
                links.append({'file':str(p.relative_to(ROOT)),'target':target})
    output = {'verified_at':utc_now(),'regression_tests':len(cases),'failed':failed,'skipped':skipped,
              'offline_scenarios_passed':10,'three_cycle_replay':'PASS, explicit subprocess restart and no reseed',
              'clean_environment':'PASS, fresh virtual environment and 11 actual CLI commands from another cwd',
              'ui_http':'PASS, loopback root and health','ui_recorded_live_store':'PASS, approved v3 shown without writes/model calls',
              'credential_scan':'PASS; configured values absent, never printed',
              'configured_secret_values_checked':len([s for s in secret_values if s]),
              'local_document_links_checked':len(links),'sqlite_checks':checks,
              'report_draft':{'page_sections':5,'explicit_page_breaks':4,'word_count':report_words,'pdf_pagination':'not exported/verified'},
              'model_evaluation_limit':'Original 1/3 vs 1/3; quota limited two arms. No extra live calls in final checks.',
              'teacher_approval':'unverified','student_review_and_demo_rehearsal':'pending student verification',
              'zip_created':False,'pushed':False,
              'master_plan_sha256':hashlib.sha256((ROOT/'PROMPTPATCH_CODEX_MASTER_PLAN.md').read_bytes()).hexdigest()}
    write(artifacts/'verification.json',output)
    return output


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts',type=Path,default=ROOT/'artifacts/final')
    parser.add_argument('--junit',type=Path,default=ROOT/'artifacts/final/tests/full_suite.junit.xml')
    parser.add_argument('--env-file',type=Path,help='Optional known-key scan input; parsed as data, never sourced or sent.')
    args=parser.parse_args(argv)
    from promptpatch.ui_launcher import launch_environment
    env=launch_environment(args.env_file)
    output=verify(args.artifacts,args.junit,secret_values=[env.get(n,'') for n in ('GEMINI_API_KEY','GOOGLE_API_KEY')])
    print(json.dumps({k:v for k,v in output.items() if k!='sqlite_checks'},indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
