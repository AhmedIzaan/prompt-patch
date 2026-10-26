"""Module 07 uses real CLI subprocesses/SQLite/Git and explicitly labeled replay."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from promptpatch.cli import main
from promptpatch.config import load_settings
from promptpatch.graph import ReviewGraph
from promptpatch.repository import Repository
from promptpatch.reviews import Reviews, cycle_by_key
from promptpatch.tool_support import read_snapshot
from scripts.seed_demo import seed_demo, SAMPLES

REPLAY = SAMPLES / "replay/module07_reviews.json"
POLICY = SAMPLES / "evaluation_policy_v2.json"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    db, repo = tmp_path / "domain.sqlite3", tmp_path / "fixture"
    seed_demo(db, repo, actor="module07-offline-fixture", approve_baseline=True)
    values = {"PROMPTPATCH_DB_PATH": str(db), "PROMPTPATCH_CHECKPOINT_DB_PATH": str(tmp_path / "checkpoints.sqlite3"),
              "PROMPTPATCH_DEMO_REPO": str(repo), "PROMPTPATCH_MODE": "replay"}
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return db, values


def cli(workspace, *args, expected=0):
    env = {key: value for key, value in os.environ.items() if not key.startswith(("GEMINI_", "PROMPTPATCH_"))}
    env.update(workspace[1])
    result = subprocess.run([sys.executable, "-m", "promptpatch.cli", *args], env=env, capture_output=True, text=True, check=False)
    assert result.returncode == expected, result.stdout + result.stderr
    return json.loads(result.stdout) if result.stdout.strip().startswith("{") else result


def start_args(key, scenario="pass_v3"):
    return ["review", "start", "--project", "demo", "--version", "v3", "--cycle", key,
            "--replay-file", str(REPLAY), "--replay-scenario", scenario]


def counts(db):
    with read_snapshot(db) as connection:
        return {table: connection.execute(f"SELECT COUNT(*) FROM {table} WHERE project_id='demo'").fetchone()[0]
                for table in ("audit_events", "review_cycles", "test_executions", "planner_decisions", "human_decisions", "tool_operations")}


def test_cli_onboarding_from_different_working_directory(tmp_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GEMINI_", "PROMPTPATCH_"))}
    env.update(PROMPTPATCH_DB_PATH=str(tmp_path / "domain.sqlite3"), PROMPTPATCH_CHECKPOINT_DB_PATH=str(tmp_path / "cp.sqlite3"),
               PROMPTPATCH_DEMO_REPO=str(tmp_path / "fixture"))
    for args in (["init"], ["demo", "seed", "--actor", "offline-cli-owner", "--approve-baseline"]):
        result = subprocess.run([sys.executable, "-m", "promptpatch.cli", *args], cwd=tmp_path, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    with Repository(tmp_path / "domain.sqlite3") as store:
        assert len(store.get_active_test_cases("demo")) == 12
    assert not (tmp_path / "cp.sqlite3").exists()


def test_review_status_start_resume_are_persistent_and_idempotent(workspace):
    result = cli(workspace, *start_args("one"))
    assert result["status"] == "completed" and result["next_action"] == "promote_candidate"
    assert result["selected_test_ids"] == ["T01"] and result["results"][0]["test_id"] == "T01"
    assert result["results"][0]["status"] == "pass"
    assert result["approval"] == "pending" and result["mode"] == "replay"
    assert result["source_refs"] and result["planner"]["reason_summary"]
    before = counts(workspace[0])
    assert cli(workspace, *start_args("one")) == result
    assert cli(workspace, "review", "resume", "--project", "demo", "--cycle", "one") == result
    assert cli(workspace, "review", "status", "--project", "demo", "--cycle", "one") == result
    assert counts(workspace[0]) == before
    changed = start_args("one") + ["--memory-off"]
    error = cli(workspace, *changed, expected=1)
    assert "different inputs" in error.stderr
    assert counts(workspace[0])["test_executions"] == 1


def test_approval_rejection_and_duplicate_boundaries(workspace):
    cli(workspace, *start_args("good"))
    args = ["version", "approve", "--project", "demo", "--version", "v3", "--cycle", "good", "--actor", "offline-owner"]
    row = cli(workspace, *args)
    assert row["decision"] == "approved"
    status = cli(workspace, "review", "status", "--project", "demo", "--cycle", "good")
    assert status["approval"] == "approved" and status["recommendation"]["approval"] == "pending"
    assert "immutable human decision" in cli(workspace, *args, expected=1).stderr
    assert counts(workspace[0])["human_decisions"] == 1
    cli(workspace, *start_args("bad", "fail_v3"))
    blocked = cli(workspace, "version", "approve", "--project", "demo", "--version", "v3", "--cycle", "bad", "--actor", "offline-owner", expected=1)
    assert "Approval requires" in blocked.stderr
    rejected = cli(workspace, "version", "reject", "--project", "demo", "--version", "v3", "--cycle", "bad", "--actor", "offline-owner", "--comments", "Synthetic developer rejection.")
    assert rejected["decision"] == "rejected"


def test_rejection_is_retrieved_and_respected_next_time(workspace):
    cli(workspace, *start_args("rejected"))
    cli(workspace, "version", "reject", "--project", "demo", "--version", "v3", "--cycle", "rejected", "--actor", "offline-owner")
    result = cli(workspace, *start_args("later"))
    assert result["recommendation"]["prior_rejection"] and result["next_action"] == "needs_review"
    assert any(ref.startswith("human_decision:") for ref in result["supplied_memory_refs"])
    assert result["approval"] == "pending"
    cli(workspace, "version", "approve", "--project", "demo", "--version", "v3", "--cycle", "later", "--actor", "offline-owner", expected=1)


@pytest.mark.parametrize("project,version", [("isolation", "v1"), ("demo", "v2")])
def test_project_or_version_mismatched_approval_is_rejected(workspace, project, version):
    cli(workspace, *start_args("belongs-to-demo"))
    cli(workspace, "version", "approve", "--project", project, "--version", version,
        "--cycle", "belongs-to-demo", "--actor", "offline-owner", expected=1)
    assert counts(workspace[0])["human_decisions"] == 0


def test_policy_proposal_approval_and_later_review_use_current_revision(workspace):
    before = cli(workspace, *start_args("before"))
    proposal = cli(workspace, "policy", "propose", "--project", "demo", "--file", str(POLICY), "--actor", "offline-owner", "--reason", "Tighten numerical tolerance.")
    assert proposal["status"] == "pending" and proposal["revision"] == 2
    with Repository(workspace[0]) as store:
        assert store.get_active_policy("demo")["revision"] == 1
    approved = cli(workspace, "policy", "approve", "--project", "demo", "--revision", "2", "--actor", "offline-owner")
    assert approved["status"] == "approved"
    with Repository(workspace[0]) as store:
        assert store.get_policy("demo", before["policy_id"])["status"] == "superseded"
        assert store.get_active_policy("demo")["id"] == approved["id"]
    cli(workspace, "policy", "approve", "--project", "demo", "--revision", "2", "--actor", "offline-owner", expected=1)
    cli(workspace, "version", "approve", "--project", "demo", "--version", "v3", "--cycle", "before", "--actor", "offline-owner", expected=1)
    after = cli(workspace, *start_args("after"))
    assert after["policy_revision"] == 2 and after["policy_id"] == approved["id"]
    memory = cli(workspace, "memory", "show", "--project", "demo")
    assert memory["active_policy"]["revision"] == 2
    assert memory["history"]["policy_corrections"][0]["proposal"]["reason"] == "Tighten numerical tolerance."


def test_stale_proposal_cannot_replace_approved_policy(workspace, tmp_path):
    args = ["policy", "propose", "--project", "demo", "--actor", "offline-owner", "--reason", "Synthetic correction."]
    cli(workspace, *args, "--file", str(POLICY))
    data = json.loads(POLICY.read_text()); data["revision"] = 3
    path = tmp_path / "third.json"; path.write_text(json.dumps(data))
    cli(workspace, *args, "--file", str(path))
    cli(workspace, "policy", "approve", "--project", "demo", "--revision", "2", "--actor", "offline-owner")
    error = cli(workspace, "policy", "approve", "--project", "demo", "--revision", "3", "--actor", "offline-owner", expected=1)
    assert "stale" in error.stderr


def test_resolved_risk_reopens_with_traceable_cycle_history(workspace):
    first = cli(workspace, *start_args("failure", "fail_v3"))
    cli(workspace, *start_args("fixed", "decimal_pass_v3"))
    with read_snapshot(workspace[0]) as db:
        risk = dict(db.execute("SELECT * FROM failure_memories WHERE project_id='demo'").fetchone())
    assert risk["status"] == "resolved"
    latest = cli(workspace, *start_args("regression", "fail_v3"))
    with Repository(workspace[0]) as store:
        reopened = store.get_failure("demo", risk["id"])
        assert reopened["status"] == "regressed" and reopened["first_cycle_id"] == first["cycle_id"]
        assert reopened["last_cycle_id"] == latest["cycle_id"]
        events = [row for row in store.get_project_timeline("demo") if row["ref_id"] == risk["id"]]
    assert [r["event_type"] for r in events] == ["failure_recorded", "failure_resolved", "failure_recorded"]


def test_resume_in_new_process_after_committed_calls_skips_completed_actions(workspace, monkeypatch):
    original = ReviewGraph.run_tests
    def interrupted(self, state):
        original(self, state)
        raise RuntimeError("synthetic interruption before node checkpoint")
    monkeypatch.setattr(ReviewGraph, "run_tests", interrupted)
    with pytest.raises(RuntimeError):
        main(start_args("interrupted", "fail_v3"))
    before = counts(workspace[0])
    assert before["test_executions"] == 2 and before["planner_decisions"] == 1
    resumed = cli(workspace, "review", "resume", "--project", "demo", "--cycle", "interrupted")
    assert resumed["next_action"] == "revise" and len(resumed["results"]) == 2
    after = counts(workspace[0])
    assert after["test_executions"] == 2 and after["planner_decisions"] == 1


def test_resume_replay_cursor_after_planning_before_execution(workspace, monkeypatch):
    def interrupted(self, state):
        raise RuntimeError("synthetic interruption before candidate calls")
    monkeypatch.setattr(ReviewGraph, "run_tests", interrupted)
    with pytest.raises(RuntimeError):
        main(start_args("cursor"))
    assert counts(workspace[0])["test_executions"] == 0
    result = cli(workspace, "review", "resume", "--project", "demo", "--cycle", "cursor")
    assert result["results"][0]["status"] == "pass" and counts(workspace[0])["planner_decisions"] == 1


def test_retry_keeps_one_result_and_log_has_attempts(workspace):
    result = cli(workspace, *start_args("retry", "retry_v3"))
    assert len(result["results"]) == 1 and result["results"][0]["status"] == "pass"
    log = cli(workspace, "logs", "show", "--project", "demo", "--cycle", "retry")
    types = [r["event_type"] for r in log["events"]]
    assert "model_call_failed" in types and "graph_memory_written" in types and "review_memory_read" in types
    assert types.count("model_call_started") == 3
    assert all(r["created_at"].endswith("+00:00") for r in log["events"])
    project_log = cli(workspace, "logs", "show", "--project", "demo")
    assert "memory_read" in [r["event_type"] for r in project_log["events"]]


@pytest.mark.parametrize("extra", [["--memory-off"], ["--replay-scenario", "not-a-scenario"]])
def test_invalid_replay_prerequisites_create_no_cycle(workspace, extra):
    args = ["review", "start", "--project", "demo", "--version", "v3", "--cycle", "no-calls"]
    if "--replay-scenario" in extra:
        args += ["--replay-file", str(REPLAY)]
    cli(workspace, *args, *extra, expected=1)
    assert counts(workspace[0])["review_cycles"] == 0


def test_missing_live_credentials_fail_before_cycle_creation(workspace, monkeypatch, capsys):
    monkeypatch.setenv("PROMPTPATCH_MODE", "live")
    monkeypatch.setenv("GEMINI_MODEL", "configured-model")
    assert main(["review", "start", "--project", "demo", "--version", "v3", "--cycle", "blocked"]) == 1
    assert "Set GEMINI_API_KEY" in capsys.readouterr().err
    assert counts(workspace[0])["review_cycles"] == 0


def test_pending_plan_is_visible_and_cannot_be_approved(workspace, capsys):
    assert main(start_args("held", "hold_v3")) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "needs_review" and result["results"] == []
    assert result["planner"]["decision"] == "HOLD_FOR_APPROVAL" and result["approval"] == "pending"
    assert main(["version", "approve", "--project", "demo", "--version", "v3", "--cycle", "held", "--actor", "offline-owner"]) == 1
    assert counts(workspace[0])["human_decisions"] == 0


def test_blank_actor_and_malformed_policy_never_create_decisions(workspace, tmp_path, capsys):
    assert main(["policy", "approve", "--project", "demo", "--revision", "1", "--actor", " "]) == 1
    path = tmp_path / "malformed.json"; path.write_text('{"revision":2,"revision":3,"private":"do-not-echo"}')
    assert main(["policy", "propose", "--project", "demo", "--file", str(path), "--actor", "offline-owner", "--reason", "test"]) == 1
    assert "do-not-echo" not in capsys.readouterr().err
    with Repository(workspace[0]) as store:
        assert store.get_active_policy("demo")["revision"] == 1


def test_approved_tolerance_changes_real_deterministic_validation(workspace, tmp_path):
    fixture = json.loads(REPLAY.read_text())
    output = json.loads(fixture["scenarios"]["pass_v3"][1]["raw_text"])
    output["estimated_settlement_mm"] = 4.005
    fixture["scenarios"]["pass_v3"][1]["raw_text"] = json.dumps(output)
    path = tmp_path / "tolerance-replay.json"; path.write_text(json.dumps(fixture))
    controller = Reviews(load_settings())
    before = controller.start("demo", "v3", "old-policy", replay_file=path, replay_scenario="pass_v3")
    assert before["results"][0]["status"] == "pass"
    from promptpatch.approvals import propose_policy, approve_policy
    pending = propose_policy(workspace[0], "demo", POLICY, actor="offline-owner", reason="Tighten tolerance in a test.")
    assert pending["status"] == "pending"
    approve_policy(workspace[0], "demo", 2, actor="offline-owner")
    after = controller.start("demo", "v3", "new-policy", replay_file=path, replay_scenario="pass_v3")
    assert after["results"][0]["status"] == "fail" and after["policy_revision"] == 2
    with Repository(workspace[0]) as store:
        assert store.get_test_execution("demo", before["results"][0]["execution_id"])["status"] == "pass"
        assert store.get_policy("demo", before["policy_id"])["status"] == "superseded"


def test_missing_checkpoint_and_changed_replay_are_clear_errors(workspace, tmp_path, capsys):
    path = tmp_path / "mutable-replay.json"; path.write_text(REPLAY.read_text())
    controller = Reviews(load_settings())
    controller.start("demo", "v3", "restore", replay_file=path, replay_scenario="pass_v3")
    path.write_text(path.read_text() + "\n")
    assert main(["review", "resume", "--project", "demo", "--cycle", "restore"]) == 1
    assert "Replay fixture changed" in capsys.readouterr().err
    path.write_text(REPLAY.read_text())
    Path(workspace[1]["PROMPTPATCH_CHECKPOINT_DB_PATH"]).unlink()
    assert main(["review", "resume", "--project", "demo", "--cycle", "restore"]) == 1
    assert "checkpoint is missing" in capsys.readouterr().err
    assert counts(workspace[0])["test_executions"] == 1


def test_cycle_and_resume_request_commit_atomically(workspace, monkeypatch):
    from promptpatch.reviews import ReviewRepository
    original = ReviewRepository._audit
    def interrupted(self, project_id, event, *args, **kwargs):
        if event == "review_requested":
            raise RuntimeError("synthetic request write interruption")
        return original(self, project_id, event, *args, **kwargs)
    monkeypatch.setattr(ReviewRepository, "_audit", interrupted)
    with pytest.raises(RuntimeError):
        main(start_args("atomic"))
    assert counts(workspace[0])["review_cycles"] == 0
    assert counts(workspace[0])["planner_decisions"] == 0
    monkeypatch.setattr(ReviewRepository, "_audit", original)
    result = cli(workspace, *start_args("atomic"))
    assert result["status"] == "completed" and counts(workspace[0])["review_cycles"] == 1


def test_timeout_setting_is_bounded_persisted_and_part_of_request(workspace, capsys):
    assert main(start_args("deadline") + ["--timeout-ms", "30000"]) == 0
    result = json.loads(capsys.readouterr().out)
    with read_snapshot(workspace[0]) as db:
        row=db.execute("SELECT decision_json FROM planner_decisions WHERE project_id='demo' AND cycle_id=?",(result["cycle_id"],)).fetchone()
    assert json.loads(row[0])["settings"]["timeout_ms"] == 30000
    assert main(start_args("deadline")) == 1
    assert "different inputs" in capsys.readouterr().err
    assert main(start_args("too-long") + ["--timeout-ms", "30001"]) == 1
    assert counts(workspace[0])["review_cycles"] == 1
