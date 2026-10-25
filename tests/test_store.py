"""Offline domain-store tests. Synthetic records are not live model evidence."""

from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from promptpatch.db import initialize_database
from promptpatch.errors import (
    DuplicateOperation, InvalidStateTransition, RecordNotFound, StoreError, SupersededPolicy,
)
from promptpatch.repository import Repository


def seed_project(repo, project_id):
    repo.create_project(project_id, f"Unit test {project_id}")
    prompt = repo.add_prompt_version(project_id, "v1", "unit-sha", "prompt.txt", "unit-hash")
    policy = repo.propose_policy_revision(project_id, {"tolerance": 0.01}, actor="tester", reason="Initial rules")
    repo.approve_policy_revision(project_id, policy["id"], actor="tester")
    case = repo.add_test_case_revision(project_id, "T01", "Synthetic 4 mm", {"value": 4}, ["unit"], actor="tester")
    cycle = repo.create_review_cycle(project_id, "c1", prompt["id"])
    return {"prompt": prompt, "policy": policy, "case": case, "cycle": cycle}


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "memory.sqlite3"
    initialize_database(path)
    with Repository(path) as repo:
        a = seed_project(repo, "a")
        b = seed_project(repo, "b")
        yield repo, a, b, path


def test_reopen_and_fresh_process_retrieve_without_reseed(tmp_path):
    path = tmp_path / "memory.sqlite3"
    initialize_database(path)
    with Repository(path) as repo:
        a = seed_project(repo, "a")
        risk = repo.record_failure("a", a["cycle"]["id"], "decimal:T01", "decimal", {"case": a["case"]["id"]})
    initialize_database(path)
    with Repository(path) as repo:
        assert repo.get_open_risks("a")[0]["id"] == risk["id"]
        assert repo.get_review_cycle("a", a["cycle"]["id"])["policy_id"] == a["policy"]["id"]
    result = subprocess.run([
        sys.executable, "-c",
        "import sys; from pathlib import Path; from promptpatch.repository import Repository; "
        "r=Repository(Path(sys.argv[1])); print(r.get_open_risks('a')[0]['id']); r.close()",
        str(path),
    ], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == risk["id"]


def test_policy_approval_history_pending_and_stale_revisions(store):
    repo, a, _, _ = store
    v1 = a["policy"]["id"]
    v2 = repo.propose_policy_revision("a", {"tolerance": 0.1}, actor="tester", reason="Correct tolerance")
    assert repo.get_active_policy("a")["id"] == v1
    with pytest.raises(InvalidStateTransition):
        repo.approve_policy_revision("a", v2["id"], actor=" ")
    repo.approve_policy_revision("a", v2["id"], actor="developer")
    assert repo.get_policy("a", v1)["status"] == "superseded"
    assert json.loads(repo.get_policy("a", v1)["rules_json"])["tolerance"] == 0.01
    assert repo.get_active_policy("a")["id"] == v2["id"]
    with pytest.raises(InvalidStateTransition):
        repo.approve_policy_revision("a", v2["id"], actor="developer")
    v3 = repo.propose_policy_revision("a", {"tolerance": 0.2}, actor="tester", reason="Candidate only")
    assert v3["status"] == "pending"
    assert repo.get_active_policy("a")["id"] == v2["id"]
    v4 = repo.propose_policy_revision("a", {"tolerance": 0.3}, actor="tester", reason="Another candidate")
    repo.approve_policy_revision("a", v4["id"], actor="tester")
    with pytest.raises(SupersededPolicy):
        repo.approve_policy_revision("a", v3["id"], actor="tester")
    with pytest.raises(SupersededPolicy):
        repo.create_review_cycle("a", "old-policy", a["prompt"]["id"], v1)
    assert repo.get_review_cycle("a", a["cycle"]["id"])["policy_id"] == v1


@pytest.mark.parametrize("record,method", [
    ("prompt", "get_prompt_version"), ("policy", "get_policy"),
    ("case", "get_test_case"), ("cycle", "get_review_cycle"),
])
def test_foreign_ids_are_not_visible(store, record, method):
    repo, _, b, _ = store
    with pytest.raises(RecordNotFound):
        getattr(repo, method)("a", b[record]["id"])


def test_cross_project_mutations_and_memory_queries(store):
    repo, a, b, _ = store
    before = repo.get_project_timeline("a")
    with pytest.raises(RecordNotFound):
        repo.create_review_cycle("a", "foreign", b["prompt"]["id"])
    with pytest.raises(RecordNotFound):
        repo.approve_policy_revision("a", b["policy"]["id"], actor="tester")
    with pytest.raises(RecordNotFound):
        repo.record_failure("a", b["cycle"]["id"], "foreign", "unit", {})
    assert repo.get_project_timeline("a") == before
    risk = repo.record_failure("b", b["cycle"]["id"], "risk", "unit", {})
    with pytest.raises(RecordNotFound):
        repo.get_failure("a", risk["id"])
    assert repo.get_open_risks("a") == []
    assert all(row["project_id"] == "a" for row in repo.get_project_timeline("a"))


def test_database_composite_fk_rejects_cross_project_even_outside_api(store):
    _, a, b, path = store
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO review_cycles(id,project_id,cycle_key,prompt_version_id,policy_id,status,created_at) "
                "VALUES(?,?,?,?,?,'pending','unit-time')",
                ("bad", "a", "foreign-fk", b["prompt"]["id"], a["policy"]["id"]),
            )


def test_duplicate_identity_and_cycle_roll_back_without_extra_audit(store):
    repo, a, _, _ = store
    before = repo.get_project_timeline("a")
    with pytest.raises(DuplicateOperation):
        repo.create_review_cycle("a", "c1", a["prompt"]["id"])
    with pytest.raises(DuplicateOperation):
        repo.add_prompt_version("a", "v1", "different-sha", "prompt.txt", "hash")
    with pytest.raises(DuplicateOperation):
        repo.create_project("a", "Duplicate")
    assert repo.get_project_timeline("a") == before


def test_test_case_revision_history_and_content_hash(store):
    repo, a, _, _ = store
    old = a["case"]
    new = repo.add_test_case_revision("a", "T01", "Synthetic 5 mm", {"value": 5}, ["unit"], actor="developer")
    assert new["revision"] == 2 and new["supersedes_id"] == old["id"]
    assert new["content_hash"] != old["content_hash"]
    assert repo.get_test_case("a", old["id"])["active"] == 0
    assert repo.get_test_case("a", old["id"])["input_text"] == old["input_text"]
    assert [row["id"] for row in repo.get_active_test_cases("a")] == [new["id"]]


def test_fail_retry_result_dedup_and_attempt_history(store):
    repo, a, b, _ = store
    cid = a["cycle"]["id"]
    repo.begin_tool_operation("a", cid, "op1", "unit-test", "request-hash")
    with pytest.raises(DuplicateOperation):
        repo.begin_tool_operation("a", cid, "op1", "unit-test", "request-hash")
    repo.finish_tool_operation("a", "op1", success=False, details={"error_code": "synthetic_timeout"})
    assert repo.get_tool_operation("a", "op1")["status"] == "failed"
    kwargs = dict(provider="offline-unit", model_id="synthetic", response={"value": 4},
                  validation={"fixture": True}, status="pass", elapsed_ms=1)
    execution = repo.record_test_execution("a", cid, a["case"]["id"], "op1", **kwargs)
    assert repo.get_tool_operation("a", "op1")["result_ref"] == execution["id"]
    assert [row["status"] for row in repo.get_operation_attempts("a", "op1")] == ["failed", "completed"]
    with pytest.raises(DuplicateOperation):
        repo.record_test_execution("a", cid, a["case"]["id"], "op1", **kwargs)
    with pytest.raises(DuplicateOperation):
        repo.finish_tool_operation("a", "op1", success=True, details={})
    with pytest.raises(RecordNotFound):
        repo.get_test_execution("b", execution["id"])
    with pytest.raises(RecordNotFound):
        repo.get_tool_operation("b", "op1")
    assert len(repo.get_operation_attempts("a", "op1")) == 2
    repo.begin_tool_operation("b", b["cycle"]["id"], "op1", "unit-test", "request-hash")
    assert repo.get_tool_operation("b", "op1")["project_id"] == "b"


def test_result_and_operation_complete_atomically_or_not_at_all(store):
    repo, a, b, _ = store
    cid = a["cycle"]["id"]
    repo.begin_tool_operation("a", cid, "op1", "unit-test", "request-hash")
    kwargs = dict(provider="offline-unit", model_id="synthetic", response={}, validation={}, status="pass", elapsed_ms=-1)
    before = repo.get_project_timeline("a")
    with pytest.raises(StoreError):
        repo.record_test_execution("a", cid, a["case"]["id"], "op1", **kwargs)
    assert repo.get_tool_operation("a", "op1")["status"] == "pending"
    assert repo.get_operation_attempts("a", "op1") == []
    assert repo.get_project_timeline("a") == before
    with pytest.raises(RecordNotFound):
        repo.record_test_execution("a", cid, b["case"]["id"], "op1", **{**kwargs, "elapsed_ms": 1})


def test_failure_resolution_regression_preserves_old_evidence_in_audit(store):
    repo, a, _, _ = store
    cid = a["cycle"]["id"]
    risk = repo.record_failure("a", cid, "risk:T01", "decimal", {"source": "old-evidence"})
    repo.resolve_failure("a", risk["id"], cid, {"source": "resolved-evidence"})
    assert repo.get_open_risks("a") == []
    c2 = repo.create_review_cycle("a", "c2", a["prompt"]["id"])
    updated = repo.record_failure("a", c2["id"], "risk:T01", "decimal", {"source": "new-evidence"})
    assert updated["id"] == risk["id"] and updated["status"] == "regressed"
    assert updated["first_cycle_id"] == cid and updated["last_cycle_id"] == c2["id"]
    assert "old-evidence" in json.dumps(repo.get_project_timeline("a"))


def test_planner_and_human_decisions_are_immutable_and_isolated(store):
    repo, a, b, _ = store
    cid = a["cycle"]["id"]
    planner = repo.record_planner_decision("a", cid, True, {"synthetic": True}, "offline-unit")
    with pytest.raises(RecordNotFound):
        repo.get_planner_decision("b", planner["id"])
    with pytest.raises(DuplicateOperation):
        repo.record_planner_decision("a", cid, True, {}, "offline-unit")
    with pytest.raises(InvalidStateTransition):
        repo.add_human_decision("a", a["prompt"]["id"], cid, "approved", actor="tester")
    repo.transition_cycle("a", cid, "running")
    repo.transition_cycle("a", cid, "completed")
    with pytest.raises(InvalidStateTransition):
        repo.transition_cycle("a", cid, "running")
    decision = repo.add_human_decision("a", a["prompt"]["id"], cid, "rejected", actor="developer", comments="Synthetic test")
    with pytest.raises(DuplicateOperation):
        repo.add_human_decision("a", a["prompt"]["id"], cid, "approved", actor="tester")
    with pytest.raises(RecordNotFound):
        repo.add_human_decision("a", b["prompt"]["id"], cid, "approved", actor="tester")
    assert repo.get_human_decisions("a")[0]["id"] == decision["id"]
    assert repo.get_human_decisions("b") == []


@pytest.mark.parametrize("table,column", [
    ("prompt_versions", "content_hash"), ("test_cases", "input_text"),
    ("evaluation_policies", "rules_json"), ("audit_events", "event_type"),
])
def test_database_rejects_historical_edits(store, table, column):
    _, _, _, path = store
    with sqlite3.connect(path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(f"UPDATE {table} SET {column}='changed' WHERE project_id='a'")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(f"DELETE FROM {table} WHERE project_id='a'")


def test_audit_timestamp_reference_and_project_archive(store):
    repo, a, _, _ = store
    event = repo.append_audit_event("a", "unit_evidence", a["case"]["id"], {"synthetic": True}, a["cycle"]["id"])
    assert datetime.fromisoformat(event["created_at"]).utcoffset() == timedelta(0)
    assert event["ref_id"] == a["case"]["id"]
    repo.archive_project("a", actor="owner")
    assert repo.get_project("a")["archived_at"] is not None
    assert repo.get_project_timeline("a")[-1]["event_type"] == "project_archived"
    with pytest.raises(InvalidStateTransition):
        repo.add_prompt_version("a", "v2", "sha", "prompt.txt", "hash")


def test_newer_schema_is_not_overwritten(tmp_path):
    path = tmp_path / "newer.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=999")
    with pytest.raises(StoreError):
        initialize_database(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 999


def test_concurrent_initialization_is_idempotent(tmp_path):
    path = tmp_path / "concurrent.sqlite3"
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(initialize_database, [path, path]))
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_audit_failure_rolls_back_domain_write(store):
    repo, _, _, path = store
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TRIGGER simulated_audit_error BEFORE INSERT ON audit_events "
                           "BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
    with pytest.raises(StoreError):
        repo.add_prompt_version("a", "v2", "sha", "prompt.txt", "hash")
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM prompt_versions WHERE project_id='a' AND label='v2'"
        ).fetchone()[0] == 0
