"""Retrieval tests use explicitly synthetic saved history, never live inference."""

import json

import pytest

from promptpatch.errors import StoreError
from promptpatch.memory_tool import MemoryTools
from promptpatch.repository import Repository
from promptpatch.tool_support import ToolError, read_snapshot
from scripts.seed_demo import seed_demo


@pytest.fixture
def history(tmp_path):
    db = tmp_path / "memory.sqlite3"
    seed_demo(db, tmp_path / "fixture", actor="offline-memory-test", approve_baseline=True)
    with read_snapshot(db) as connection:
        versions = {project: connection.execute(
            "SELECT id FROM prompt_versions WHERE project_id=? AND label='v1'", (project,)
        ).fetchone()[0] for project in ("demo", "isolation")}
    with Repository(db) as store:
        cases = {row["case_key"]: row for row in store.get_active_test_cases("demo")}
        c1 = store.create_review_cycle("demo", "synthetic-c1", versions["demo"])
        c2 = store.create_review_cycle("demo", "synthetic-c2", versions["demo"])
        risk = store.record_failure("demo", c1["id"], "decimal:T02", "decimal", {"source": "old-synthetic-evidence"})
        store.resolve_failure("demo", risk["id"], c1["id"], {"source": "synthetic-resolution"})
        store.record_failure("demo", c2["id"], "decimal:T02", "decimal", {"source": "synthetic-regression"})
        store.record_failure("demo", c2["id"], "decimal:T07", "decimal", {"source": "second-decimal"})
        store.record_failure("demo", c1["id"], "missing:T04", "missing_value", {})
        resolved = store.record_failure("demo", c1["id"], "unit:T11", "unit", {})
        store.resolve_failure("demo", resolved["id"], c2["id"], {})
        store.begin_tool_operation("demo", c1["id"], "synthetic-op", "unit-test", "synthetic-hash")
        execution = store.record_test_execution("demo", c1["id"], cases["T02"]["id"], "synthetic-op",
                                                provider="offline-unit", model_id="synthetic", response={"raw": "omitted"},
                                                validation={"mismatch": "synthetic-decimal"}, status="fail", elapsed_ms=1)
        store.transition_cycle("demo", c1["id"], "running")
        store.transition_cycle("demo", c1["id"], "completed")
        human = store.add_human_decision("demo", versions["demo"], c1["id"], "rejected", actor="offline-owner",
                                         comments="Private synthetic developer feedback")
        rules = json.loads(store.get_active_policy("demo")["rules_json"])
        rules["numeric_absolute_tolerance_mm"] = 0.001
        policy = store.propose_policy_revision("demo", rules, actor="offline-owner", reason="Synthetic approved correction")
        store.approve_policy_revision("demo", policy["id"], actor="offline-owner")
        pending = store.propose_policy_revision("demo", {**rules, "numeric_absolute_tolerance_mm": 0.5},
                                               actor="offline-owner", reason="Synthetic pending correction")
        corrected = store.add_test_case_revision("demo", "T02", cases["T02"]["input_text"],
                                                  json.loads(cases["T02"]["expected_json"]),
                                                  ["decimal", "corrected"], actor="offline-owner")
        other_cycle = store.create_review_cycle("isolation", "synthetic-other", versions["isolation"])
        store.record_failure("isolation", other_cycle["id"], "private-other", "decimal", {"source": "ISOLATION-PRIVATE"})
    return db, MemoryTools(db), {"risk": risk, "human": human, "policy": policy,
                                 "pending": pending, "corrected": corrected, "execution": execution}


def test_reads_prior_risk_history_outcomes_feedback_and_corrections(history):
    _, tool, saved = history
    result = tool.retrieve_memory("demo")
    assert len(result["risks"]) == 3
    assert any(row["status"] == "regressed" for row in result["risks"])
    assert "old-synthetic-evidence" in json.dumps(result["failure_history"])
    assert result["outcomes"][0]["id"] == saved["execution"]["id"]
    assert result["outcomes"][0]["validation"]["mismatch"] == "synthetic-decimal"
    assert "response" not in result["outcomes"][0]
    assert result["human_decisions"][0]["id"] == saved["human"]["id"]
    assert result["policy_corrections"][0]["id"] == saved["policy"]["id"]
    assert result["policy_corrections"][0]["proposal"]["reason"] == "Synthetic approved correction"
    assert result["case_corrections"][0]["id"] == saved["corrected"]["id"]
    assert result["case_corrections"][0]["attribution"]["actor"] == "offline-owner"
    assert saved["pending"]["id"] not in json.dumps(result)
    assert "ISOLATION-PRIVATE" not in json.dumps(result)
    assert f"risk:{saved['risk']['id']}" in result["source_refs"]
    for name in ("risks", "outcomes", "human_decisions", "policy_corrections", "case_corrections"):
        assert all(row["project_id"] == "demo" for row in result[name])


def test_tags_limit_and_open_filter_are_explicit(history):
    _, tool, _ = history
    decimal = tool.retrieve_memory("demo", tags=["decimal"])
    assert len(decimal["risks"]) == 2
    assert all(row["category"] == "decimal" for row in decimal["risks"])
    assert decimal["human_decisions"] and decimal["policy_corrections"]
    assert len(tool.retrieve_memory("demo", open_only=False)["risks"]) == 4
    limited = tool.retrieve_memory("demo", limit=1)
    for name, truncated in limited["truncated"].items():
        assert len(limited[name]) <= 1
    assert limited["truncated"]["risks"] is True
    no_tags = tool.retrieve_memory("demo", tags=["decimal') OR 1=1--"])
    assert no_tags["risks"] == [] and no_tags["outcomes"] == []


def test_isolation_project_never_sees_main_history(history):
    _, tool, saved = history
    result = tool.retrieve_memory("isolation")
    assert result["risks"][0]["evidence"]["source"] == "ISOLATION-PRIVATE"
    assert result["outcomes"] == [] and result["human_decisions"] == []
    assert result["policy_corrections"] == [] and result["case_corrections"] == []
    assert saved["risk"]["id"] not in json.dumps(result)
    assert saved["human"]["id"] not in json.dumps(result)


def test_only_approved_active_policy_is_returned(history):
    _, tool, saved = history
    result = tool.read_active_policy("demo")
    assert result["status"] == "approved" and result["revision"] == 2
    assert result["id"] == saved["policy"]["id"]
    assert result["id"] != saved["pending"]["id"]
    assert result["rules"]["numeric_absolute_tolerance_mm"] == 0.001
    assert tool.read_active_policy("isolation")["revision"] == 1


@pytest.mark.parametrize("kwargs", [{"limit": 0}, {"limit": 51}, {"limit": True},
                                    {"open_only": "yes"}, {"tags": "decimal"}, {"tags": [""]}])
def test_invalid_filters_fail_and_are_audited(history, kwargs):
    db, tool, _ = history
    with pytest.raises(ToolError) as error:
        tool.retrieve_memory("demo", **kwargs)
    assert error.value.code == "invalid_filter"
    with Repository(db) as store:
        last = store.get_project_timeline("demo")[-1]
        assert last["event_type"] == "tool_failed"
        assert json.loads(last["details_json"])["error_code"] == "invalid_filter"


def test_bounded_output_and_no_raw_feedback_in_tool_audits(history):
    db, tool, _ = history
    tool.retrieve_memory("demo")
    with pytest.raises(ToolError) as error:
        MemoryTools(db, max_memory_bytes=1).retrieve_memory("demo")
    assert error.value.code == "memory_limit"
    with Repository(db) as store:
        events = [row for row in store.get_project_timeline("demo")
                  if row["event_type"] in {"tool_invoked", "memory_read", "tool_succeeded", "tool_failed"}]
    assert any(event["event_type"] == "memory_read" for event in events)
    log = json.dumps(events)
    assert "Private synthetic developer feedback" not in log
    assert "old-synthetic-evidence" not in log


def test_unknown_archived_and_missing_database_fail_without_foreign_audit(history, tmp_path):
    db, tool, _ = history
    with Repository(db) as store:
        before = store.get_project_timeline("demo")
    with pytest.raises(ToolError) as error:
        tool.retrieve_memory("unknown-project")
    assert error.value.code == "project_unavailable"
    with Repository(db) as store:
        assert store.get_project_timeline("demo") == before
        store.archive_project("demo", actor="offline-owner")
        archived = store.get_project_timeline("demo")
    with pytest.raises(ToolError) as error:
        tool.retrieve_memory("demo")
    assert error.value.code == "project_unavailable"
    with Repository(db) as store:
        assert store.get_project_timeline("demo") == archived
    with pytest.raises(ToolError) as error:
        MemoryTools(tmp_path / "missing.sqlite3").retrieve_memory("demo")
    assert error.value.code == "audit_unavailable"
    assert not (tmp_path / "missing.sqlite3").exists()


def test_missing_approved_policy_fails_closed(history):
    db, tool, _ = history
    with Repository(db) as store:
        store.create_project("empty", "No approved policy")
        store.propose_policy_revision("empty", {}, actor="offline-owner", reason="Pending only")
    with pytest.raises(ToolError) as error:
        tool.read_active_policy("empty")
    assert error.value.code == "no_approved_policy"


def test_audit_failure_never_returns_success(history, monkeypatch):
    _, tool, _ = history
    original = Repository.append_audit_event

    def fail_success(self, project_id, event_type, *args, **kwargs):
        if event_type == "tool_succeeded":
            raise StoreError("Synthetic audit outage")
        return original(self, project_id, event_type, *args, **kwargs)

    monkeypatch.setattr(Repository, "append_audit_event", fail_success)
    with pytest.raises(ToolError) as error:
        tool.read_active_policy("demo")
    assert error.value.code == "audit_unavailable"
