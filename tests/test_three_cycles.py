"""Three real application processes; handwritten replay is never live evidence."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from scripts.run_three_cycles import DemoError, DemoRun

ROOT = Path(__file__).resolve().parents[1]


def invoke(tmp_path, stage, *extra, expected=0):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GEMINI_", "PROMPTPATCH_"))}
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_three_cycles.py'), stage,
                             '--mode','replay','--runtime',str(tmp_path / 'runtime'),
                             '--artifacts',str(tmp_path / 'exports'),'--repo',str(tmp_path / 'git'),*extra],
                            cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == expected, result.stdout + result.stderr
    return result


def count_results(tmp_path):
    with sqlite3.connect(tmp_path / 'runtime/memory.sqlite3') as db:
        return {t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
                for t in ('test_executions','review_cycles','planner_decisions','audit_events','evaluation_policies','human_decisions')}


def test_three_cli_processes_restart_correction_and_idempotent_runner(tmp_path):
    prepared=json.loads(invoke(tmp_path,'prepare').stdout)
    assert prepared['phase']=='prepared' and prepared['approval']=='pending'
    manifest=json.loads((tmp_path / 'runtime/demo_run.json').read_text())
    assert manifest['commands']['cycle_2']['confirmed_exit']
    with sqlite3.connect(tmp_path / 'runtime/memory.sqlite3') as db:
        assert db.execute("SELECT status FROM evaluation_policies WHERE project_id='demo' AND revision=2").fetchone()[0]=='pending'
        assert db.execute("SELECT COUNT(*) FROM review_cycles WHERE project_id='demo'").fetchone()[0]==2
    before=count_results(tmp_path)
    # Recover an export lost after the worker result was already checkpointed.
    (tmp_path / 'exports/cycle_1.json').unlink()
    recovery=DemoRun(tmp_path/'runtime',tmp_path/'exports','replay',repo=tmp_path/'git')
    recovery.cli('cycle_1', [], review=True)
    assert (tmp_path / 'exports/cycle_1.json').exists() and count_results(tmp_path)==before
    invoke(tmp_path,'finish',expected=1)
    assert count_results(tmp_path)==before
    reference='Synthetic offline test owner approval, not a student/teacher approval.'
    summary=json.loads(invoke(tmp_path,'finish','--approve-policy','--actor','synthetic-test-owner','--approval-reference',reference).stdout)
    assert summary['mode']=='replay' and not summary['live_inference']
    assert [c['recommendation'] for c in summary['cycles']]==['revise','revise','promote_candidate']
    assert [c['policy_revision'] for c in summary['cycles']]==[1,1,2]
    assert summary['cycles'][0]['supplied_risk_ids']==[]
    assert summary['cycles'][1]['prior_failed_cases_retested']==['T02','T03']
    assert summary['cycles'][2]['prior_failed_cases_retested']==['T03','T04']
    assert all(c['approval']=='pending' for c in summary['cycles'])
    process=json.loads((tmp_path / 'exports/process_evidence.json').read_text())
    assert process['cycle2_process']['pid']!=process['cycle3_process']['pid']
    assert process['cycle2_process']['exited_at'] < process['cycle3_process']['started_at']
    assert process['source_identity_before']==process['source_identity_after'] and not process['seed_after_cycle2']
    for number in (1,2,3):
        cycle=json.loads((tmp_path / f'exports/cycle_{number}.json').read_text())
        assert cycle['checkpoint_count']>=10
        assert all(r['response']['mode']=='replay' and r['response']['usage']=={} for r in cycle['executions'])
    with sqlite3.connect(tmp_path / 'runtime/memory.sqlite3') as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert db.execute("SELECT COUNT(*) FROM failure_memories WHERE project_id='demo' AND status='resolved'").fetchone()[0]==3
        assert db.execute("SELECT COUNT(*) FROM human_decisions").fetchone()[0]==0
    after=count_results(tmp_path)
    invoke(tmp_path,'prepare')
    repeated=json.loads(invoke(tmp_path,'finish').stdout)
    assert repeated==summary and count_results(tmp_path)==after
    assert (tmp_path / 'exports/restart_evidence.txt').is_file()


def test_unowned_directory_is_not_overwritten(tmp_path, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    runtime=tmp_path/'private'; runtime.mkdir(); (runtime/'keep.txt').write_text('owner data')
    with pytest.raises(DemoError,match='unowned'):
        DemoRun(runtime,tmp_path/'exports','replay',repo=tmp_path/'git')
    assert (runtime/'keep.txt').read_text()=='owner data'
    assert not (runtime/'demo_run.json').exists()


def test_finish_requires_completed_prepare(tmp_path):
    result=invoke(tmp_path,'finish','--approve-policy','--actor','test','--approval-reference','test',expected=1)
    assert 'blocked' in result.stderr
    assert not (tmp_path/'runtime/memory.sqlite3').exists()


def test_configuration_cannot_change_on_an_existing_run(tmp_path):
    original=DemoRun(tmp_path/'runtime',tmp_path/'exports','replay',repo=tmp_path/'git')
    with pytest.raises(DemoError,match='configuration differs'):
        DemoRun(tmp_path/'runtime',tmp_path/'exports','replay',repo=tmp_path/'different-git')
    assert original.manifest['phase']=='new'
