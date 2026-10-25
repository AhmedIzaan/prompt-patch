"""Offline coordinator/decision tests; all provider responses are labeled replay."""
import copy
import json
import sqlite3
import subprocess
import sys

import pytest

from promptpatch.errors import RecordNotFound
from promptpatch.git_tool import GitEvidenceTool, RepositoryAccess
from promptpatch.graph import ReviewGraph
from promptpatch.model_provider import ModelSettings, ProviderError, ProviderResponse
from promptpatch.planner import validate_decision, planner_schema
from promptpatch.repository import Repository, encode
from promptpatch.tool_support import read_snapshot
from scripts.seed_demo import seed_demo, PROMPT_PATH, SAMPLES


class ScriptedProvider:
    name, mode = "replay", "replay"

    def __init__(self, ids=None, decision="RUN_TESTS", *, bad=False, fail_candidate=False, fail_planner=False):
        self.ids = ids if ids is not None else ["T01", "T02"]
        self.decision, self.bad = decision, bad
        self.fail_candidate, self.fail_planner = fail_candidate, fail_planner
        self.calls, self.inputs = [], []
        self.outputs = {case["input_text"]: case["expected"] for case in json.loads((SAMPLES / "test_cases.json").read_text())["cases"]}

    def generate_once(self, prompt, input_text, settings, *, purpose, response_schema):
        self.calls.append(purpose)
        if (purpose == "planner" and self.fail_planner) or (purpose != "planner" and self.fail_candidate):
            raise ProviderError("invalid_request")
        if purpose == "planner":
            context = json.loads(input_text)
            self.inputs.append(context)
            value = {"decision": self.decision, "test_ids": self.ids if self.decision == "RUN_TESTS" else [],
                     "test_mode": "targeted_regression", "reason_summary": "Synthetic offline plan for routing tests.",
                     "memory_evidence_ids": [], "source_evidence_refs": [context["source_refs"][0]],
                     "needs_developer_approval": self.decision != "RUN_TESTS"}
            raw = "invalid" if self.bad else encode(value)
        else:
            value = copy.deepcopy(self.outputs[input_text])
            # Deliberately incorrect decimal fixture; no claim of live inference.
            if value["estimated_settlement_mm"] == 4.5:
                value["estimated_settlement_mm"] = 5.0
            raw = encode(value)
        return ProviderResponse(provider="replay", mode="replay", purpose=purpose, model_id=settings.model_id,
                                raw_text=raw, elapsed_ms=0, usage={}, finish_reason="REPLAY",
                                fixture_id="module06-offline-test-double")


@pytest.fixture
def setup(tmp_path):
    db, root, checkpoint = tmp_path / "domain.sqlite3", tmp_path / "git", tmp_path / "checkpoints.sqlite3"
    seed_demo(db, root, actor="offline-graph-fixture", approve_baseline=True)
    git = GitEvidenceTool(db, {p: RepositoryAccess(root, frozenset({PROMPT_PATH})) for p in ("demo", "isolation")})
    with read_snapshot(db) as conn:
        versions = {row["label"]: row["id"] for row in conn.execute("SELECT * FROM prompt_versions WHERE project_id='demo'")}
    with Repository(db) as store:
        cycle = store.create_review_cycle("demo", "graph-test", versions["v2"])
    return db, checkpoint, git, cycle["id"], versions


def graph(setup, provider):
    return ReviewGraph(setup[0], setup[1], setup[2], provider, ModelSettings(model_id="offline-replay", max_attempts=1))


def counts(db):
    with read_snapshot(db) as conn:
        return {table: conn.execute(f"SELECT COUNT(*) FROM {table} WHERE project_id='demo'").fetchone()[0]
                for table in ("test_executions", "planner_decisions", "failure_memories", "tool_operations", "audit_events", "human_decisions")}


def test_real_graph_executes_only_planner_choices_and_reuses_checkpoint(setup):
    provider = ScriptedProvider()
    runner = graph(setup, provider)
    result = runner.run("demo", setup[3], base_version_id=setup[4]["v1"])
    assert result["error"] is None
    assert result["selected_test_ids"] == ["T01", "T02"]
    assert [r["test_id"] for r in result["execution_results"]] == result["selected_test_ids"]
    assert result["recommendation"]["action"] == "revise"
    assert result["pending_approval"] and counts(setup[0])["human_decisions"] == 0
    assert provider.calls == ["planner", "candidate_execution", "candidate_execution"]
    before = counts(setup[0])
    assert before["failure_memories"] == 1
    assert runner.run("demo", setup[3], base_version_id=setup[4]["v1"]) == result
    assert counts(setup[0]) == before and len(provider.calls) == 3
    with sqlite3.connect(setup[1]) as db:
        assert db.execute("SELECT COUNT(*) FROM checkpoints WHERE thread_id=?", (f"demo:{setup[3]}",)).fetchone()[0] >= 10
    # New OS process loads the strict SQLite checkpoint, with no provider available.
    code = """import sqlite3,sys
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
s=SqliteSaver(sqlite3.connect(sys.argv[1]),serde=JsonPlusSerializer(allowed_msgpack_modules=[],allowed_json_modules=[]))
v=s.get_tuple({'configurable':{'thread_id':sys.argv[2]}}).checkpoint['channel_values']
print(v['next_action'])
"""
    child = subprocess.run([sys.executable, "-c", code, str(setup[1]), f"demo:{setup[3]}"], capture_output=True, text=True, check=True)
    assert child.stdout.strip() == "revise"


@pytest.mark.parametrize("decision", ["REQUEST_CLARIFICATION", "HOLD_FOR_APPROVAL"])
def test_nonexecuting_routes(setup, decision):
    provider = ScriptedProvider(decision=decision)
    result = graph(setup, provider).run("demo", setup[3])
    assert result["selected_test_ids"] == [] and result["execution_results"] == []
    assert result["recommendation"]["planner_action"] == decision.lower()
    assert result["next_action"] == "needs_review" and provider.calls == ["planner"]
    with Repository(setup[0]) as store:
        assert store.get_review_cycle("demo", setup[3])["status"] == "needs_review"


@pytest.mark.parametrize("options", [{"bad": True}, {"ids": ["T01", "FOREIGN"]}, {"ids": ["T02"]},
                                       {"ids": ["T01", "T01"]}, {"ids": ["T01", "T02", "T03", "T04", "T05"]},
                                       {"fail_planner": True}])
def test_invalid_plans_and_failures_fail_closed(setup, options):
    provider = ScriptedProvider(**options)
    result = graph(setup, provider).run("demo", setup[3])
    assert result["error"] and result["next_action"] == "needs_review"
    assert provider.calls == ["planner"] and counts(setup[0])["test_executions"] == 0
    assert counts(setup[0])["planner_decisions"] == 1


def test_candidate_failure_has_no_invented_result(setup):
    provider = ScriptedProvider(fail_candidate=True)
    result = graph(setup, provider).run("demo", setup[3])
    assert result["error"] == "invalid_request" and result["next_action"] == "needs_review"
    assert result["execution_results"] == [] and counts(setup[0])["test_executions"] == 0


def test_memory_toggle_only_changes_history_in_planner_input(setup):
    db = setup[0]
    with Repository(db) as store:
        store.record_failure("demo", setup[3], "synthetic-risk", "decimal", {"test_id": "T02"})
        second = store.create_review_cycle("demo", "off", setup[4]["v2"])
    on, off = ScriptedProvider(decision="HOLD_FOR_APPROVAL"), ScriptedProvider(decision="HOLD_FOR_APPROVAL")
    graph(setup, on).run("demo", setup[3])
    graph(setup, off).run("demo", second["id"], memory_enabled=False)
    left, right = copy.deepcopy(on.inputs[0]), copy.deepcopy(off.inputs[0])
    assert left.pop("long_term_memory")["risks"]
    assert right.pop("long_term_memory") is None
    assert left == right
    with Repository(db) as store:
        decision = store.get_planner_decision("demo", graph(setup, on).run("demo", setup[3])["planner_decision_id"])
    assert json.loads(decision["decision_json"])["supplied_memory_refs"]


def test_project_and_checkpoint_configuration_isolation(setup):
    runner = graph(setup, ScriptedProvider())
    with pytest.raises(RecordNotFound):
        runner.run("isolation", setup[3])
    assert not setup[1].exists()
    runner.run("demo", setup[3])
    with pytest.raises(ValueError, match="checkpoint_request_changed"):
        runner.run("demo", setup[3], memory_enabled=False)
    with pytest.raises(ValueError, match="separate"):
        ReviewGraph(setup[0], setup[0], setup[2], ScriptedProvider(), ModelSettings(model_id="offline"))


def test_memory_write_reentry_does_not_duplicate_events(setup):
    runner = graph(setup, ScriptedProvider())
    state = runner.run("demo", setup[3])
    before = counts(setup[0])
    runner.write_memory_and_audit(state)
    runner.prepare_recommendation(state)
    assert counts(setup[0]) == before


def test_guard_rejects_fabricated_refs(setup):
    provider = ScriptedProvider(decision="HOLD_FOR_APPROVAL")
    state = graph(setup, provider).run("demo", setup[3])
    context = ReviewGraph.planner_context(state)
    value = state["planner_decision"]
    for field in ("memory_evidence_ids", "source_evidence_refs"):
        with pytest.raises(ValueError):
            validate_decision({**value, field: ["risk:other-project"]}, context)


def test_success_recommends_candidate_without_approval(setup):
    result = graph(setup, ScriptedProvider(ids=["T01", "T07", "T09"])).run("demo", setup[3])
    assert result["next_action"] == "promote_candidate" and result["pending_approval"]
    assert counts(setup[0])["human_decisions"] == 0


def test_uncertain_cannot_promote(setup):
    result = graph(setup, ScriptedProvider(ids=["T01", "T08"])).run("demo", setup[3])
    assert result["execution_results"][-1]["status"] == "uncertain"
    assert result["next_action"] == "needs_review"


def test_resume_after_completed_calls_before_node_checkpoint(setup):
    provider = ScriptedProvider()
    runner = graph(setup, provider)
    original = runner.run_tests

    def interrupted(state):
        original(state)  # All results commit, but no graph update is checkpointed.
        raise RuntimeError("synthetic interruption after durable execution")

    runner.run_tests = interrupted
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        runner.run("demo", setup[3])
    assert counts(setup[0])["test_executions"] == 2
    resumed = graph(setup, provider).run("demo", setup[3])
    assert resumed["next_action"] == "revise"
    assert provider.calls == ["planner", "candidate_execution", "candidate_execution"]
    assert counts(setup[0])["test_executions"] == 2


def test_planner_decision_commit_gap_reuses_saved_response(setup):
    provider = ScriptedProvider(decision="HOLD_FOR_APPROVAL")
    runner = graph(setup, provider)
    original = runner.planner.decide

    def interrupted(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("synthetic interruption after durable planning")

    runner.planner.decide = interrupted
    with pytest.raises(RuntimeError):
        runner.run("demo", setup[3])
    resumed = graph(setup, provider).run("demo", setup[3])
    assert resumed["next_action"] == "needs_review"
    assert provider.calls == ["planner"] and counts(setup[0])["planner_decisions"] == 1


def test_retrieved_memory_contains_only_current_project(setup):
    with Repository(setup[0]) as store:
        foreign_case = store.get_active_test_cases("isolation")[0]
        with read_snapshot(setup[0]) as db:
            version = db.execute("SELECT id FROM prompt_versions WHERE project_id='isolation'").fetchone()[0]
        foreign = store.create_review_cycle("isolation", "foreign-private", version)
        store.record_failure("isolation", foreign["id"], "foreign-secret-marker", "decimal", {"private": "other-project-marker"})
    provider = ScriptedProvider(decision="HOLD_FOR_APPROVAL")
    graph(setup, provider).run("demo", setup[3])
    assert "other-project-marker" not in encode(provider.inputs)
    assert foreign_case["id"] not in encode(provider.inputs)


def test_guard_accepts_supplied_memory_ids_and_exact_refs(setup):
    with Repository(setup[0]) as store:
        risk = store.record_failure("demo", setup[3], "known-risk", "decimal", {"test_id": "T02"})
    provider = ScriptedProvider(decision="HOLD_FOR_APPROVAL")
    state = graph(setup, provider).run("demo", setup[3])
    context = ReviewGraph.planner_context(state)
    for reference in (risk["id"], "risk:" + risk["id"]):
        plan = validate_decision({**state["planner_decision"], "memory_evidence_ids": [reference]}, context)
        assert plan.memory_evidence_ids == [reference]


def test_strict_serializer_disables_pickle_and_dynamic_types(setup):
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    serializer = JsonPlusSerializer(pickle_fallback=False, allowed_json_modules=[], allowed_msgpack_modules=[])
    assert not serializer.pickle_fallback
    assert serializer.loads_typed(serializer.dumps_typed({"state": ["plain", 1, None]})) == {"state": ["plain", 1, None]}
    with pytest.raises(NotImplementedError):
        serializer.loads_typed(("pickle", b"untrusted"))


def test_schema_bounds_citations_without_selecting_tests(setup):
    with Repository(setup[0]) as store:
        risk = store.record_failure("demo", setup[3], "schema-risk", "decimal", {"test_id": "T02"})
    provider = ScriptedProvider(decision="HOLD_FOR_APPROVAL")
    state = graph(setup, provider).run("demo", setup[3])
    context = ReviewGraph.planner_context(state)
    schema = planner_schema(context)
    assert "risk:" + risk["id"] in schema["properties"]["memory_evidence_ids"]["items"]["enum"]
    assert "enum" not in schema["properties"]["test_ids"]["items"]
    assert schema["properties"]["memory_evidence_ids"]["maxItems"] <= 8
    context["long_term_memory"] = None
    assert planner_schema(context)["properties"]["memory_evidence_ids"]["maxItems"] == 0
