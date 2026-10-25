"""Single persisted coordinator. Domain SQLite remains authoritative.

Use one worker per cycle. Checkpoints must be trusted local files, separate from
source/domain storage. Completed external operations are never blindly reissued.
"""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from typing import TypedDict

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langsmith import tracing_context

from promptpatch.errors import StoreError
from promptpatch.evaluator import SettlementEvaluator
from promptpatch.executor import ExecutionError, TestExecutor
from promptpatch.memory_tool import MemoryTools
from promptpatch.model_provider import ProviderError
from promptpatch.planner import Planner, validate_decision
from promptpatch.repository import Repository, digest, encode
from promptpatch.tool_support import ToolError, read_snapshot


class AgentState(TypedDict, total=False):
    project_id: str
    cycle_id: str
    version_id: str
    base_version_id: str | None
    policy_id: str
    memory_enabled: bool
    settings_hash: str
    policy: dict
    catalog: list[dict]
    git_evidence: dict
    memory: dict | None
    memory_refs: list[str]
    planner_decision: dict | None
    planner_decision_id: str
    selected_test_ids: list[str]
    execution_results: list[dict]
    risk_changes: list[dict]
    next_action: str
    pending_approval: bool
    error: str | None
    recommendation: dict


class ReviewGraph:
    def __init__(self, db_path, checkpoint_path, git_tool, provider, model_settings):
        self.db_path, self.checkpoint_path = Path(db_path), Path(checkpoint_path)
        if self.db_path.resolve() == self.checkpoint_path.resolve():
            raise ValueError("Checkpoint and domain databases must be separate.")
        self.git, self.provider, self.settings = git_tool, provider, model_settings
        self.memory = MemoryTools(self.db_path)
        self.planner = Planner(self.db_path, provider, model_settings)
        self.executor = TestExecutor(self.db_path, provider)

    def _once(self, state, event, details):
        with read_snapshot(self.db_path) as db:
            exists = db.execute("SELECT 1 FROM audit_events WHERE project_id=? AND cycle_id=? AND event_type=? LIMIT 1",
                                (state["project_id"], state["cycle_id"], event)).fetchone()
        if not exists:
            with Repository(self.db_path) as store:
                store.append_audit_event(state["project_id"], event, state["cycle_id"], details, state["cycle_id"])

    def _wrapped(self, name):
        def node(state):
            try:
                result = getattr(self, name)(state)
            except (StoreError, ToolError, ExecutionError, ProviderError, ValueError) as exc:
                result = {"error": getattr(exc, "code", "invalid_context_or_state"), "next_action": "needs_review"}
            self._once(state, "graph_node_" + name, {"node": name, "error": result.get("error"),
                                                     "selected_test_ids": result.get("selected_test_ids", [])})
            return result
        return node

    @contextmanager
    def compiled(self):
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.checkpoint_path, check_same_thread=False)
        try:
            saver = SqliteSaver(conn, serde=JsonPlusSerializer(pickle_fallback=False,
                                allowed_json_modules=[], allowed_msgpack_modules=[]))
            builder = StateGraph(AgentState)
            names = ["load_context", "read_sources", "read_long_term_memory", "plan_tests", "validate_plan",
                     "run_tests", "validate_outputs", "reconcile_failures", "write_memory_and_audit", "prepare_recommendation"]
            for name in names:
                builder.add_node(name, self._wrapped(name))
            builder.add_edge(START, names[0])
            for left, right in zip(names[:4], names[1:5]):
                builder.add_edge(left, right)
            builder.add_conditional_edges("validate_plan", lambda s: "run" if s.get("next_action") == "run_tests" else "pending",
                                          {"run": "run_tests", "pending": "prepare_recommendation"})
            for left, right in zip(names[5:], names[6:]):
                builder.add_edge(left, right)
            builder.add_edge("prepare_recommendation", END)
            yield builder.compile(checkpointer=saver)
        finally:
            conn.close()

    def run(self, project_id, cycle_id, *, memory_enabled=True, base_version_id=None):
        # Authorize project ownership BEFORE looking up a checkpoint/thread.
        with Repository(self.db_path) as store:
            project = store.get_project(project_id)
            cycle = store.get_review_cycle(project_id, cycle_id)
            if project["archived_at"]:
                raise ValueError("project_archived")
            if base_version_id:
                store.get_prompt_version(project_id, base_version_id)
        settings_hash = digest({"settings": self.settings.model_dump(), "provider": self.provider.name, "mode": self.provider.mode})
        config = {"configurable": {"thread_id": f"{project_id}:{cycle_id}"}, "callbacks": [], "recursion_limit": 30}
        initial = {"project_id": project_id, "cycle_id": cycle_id, "version_id": cycle["prompt_version_id"],
                   "base_version_id": base_version_id, "memory_enabled": memory_enabled, "settings_hash": settings_hash,
                   "selected_test_ids": [], "execution_results": [], "risk_changes": [], "error": None,
                   "pending_approval": True, "next_action": "load_context"}
        # Do not export source text or model responses to optional hosted tracing.
        with tracing_context(enabled=False), self.compiled() as graph:
            snapshot = graph.get_state(config)
            if snapshot.values:
                if any(snapshot.values.get(key) != initial[key] for key in
                       ("project_id", "cycle_id", "version_id", "base_version_id", "memory_enabled", "settings_hash")):
                    raise ValueError("checkpoint_request_changed")
                if not snapshot.next:
                    return dict(snapshot.values)
                return graph.invoke(None, config)
            if cycle["status"] != "pending":
                raise ValueError("nonpending_cycle_without_checkpoint")
            return graph.invoke(initial, config)

    def load_context(self, state):
        p, c = state["project_id"], state["cycle_id"]
        policy = self.memory.read_active_policy(p)
        with Repository(self.db_path) as store:
            cycle = store.get_review_cycle(p, c)
            if cycle["policy_id"] != policy["id"]:
                raise ValueError("cycle_policy_is_not_current")
            catalog = [{"id": row["id"], "test_id": row["case_key"], "tags": json.loads(row["tags_json"]),
                        "input_text": row["input_text"], "source_ref": f"case:{row['id']}"}
                       for row in store.get_active_test_cases(p) if row["case_key"] in policy["rules"]["allowed_test_ids"]]
            if len(catalog) > 50 or len(encode(catalog).encode()) > 65536:
                raise ValueError("catalog_budget_exceeded")
            if cycle["status"] == "pending":
                store.transition_cycle(p, c, "running")
        return {"policy_id": policy["id"], "policy": {"id": policy["id"], "rules": policy["rules"],
                "source_ref": policy["source_ref"]}, "catalog": catalog}

    def _prompt(self, state):
        with Repository(self.db_path) as store:
            version = store.get_prompt_version(state["project_id"], state["version_id"])
        return self.git.read_git_prompt(state["project_id"], version["git_commit_sha"], version["prompt_path"])

    def read_sources(self, state):
        if state.get("error"):
            return {}
        prompt = self._prompt(state)
        evidence = {"prompt": prompt.model_dump(), "diff": None, "source_refs": [prompt.source_ref]}
        if state.get("base_version_id"):
            with Repository(self.db_path) as store:
                base = store.get_prompt_version(state["project_id"], state["base_version_id"])
            diff = self.git.compare_prompt_versions(state["project_id"], base["git_commit_sha"], prompt.commit_sha, prompt.prompt_relpath)
            evidence["diff"] = diff.model_dump()
            if len(encode(evidence["diff"]).encode()) > 16384:
                raise ValueError("diff_budget_exceeded")
            evidence["source_refs"].extend(diff.source_refs)
        return {"git_evidence": evidence}

    def read_long_term_memory(self, state):
        if state.get("error"):
            return {}
        memory = self.memory.retrieve_memory(state["project_id"], limit=10) if state["memory_enabled"] else None
        return {"memory": memory, "memory_refs": memory["source_refs"] if memory else []}

    @staticmethod
    def planner_context(state):
        return {"current_source": state["git_evidence"], "policy": state["policy"], "catalog": state["catalog"],
                "long_term_memory": state["memory"], "source_refs": list(dict.fromkeys(
                    state["git_evidence"]["source_refs"] + [state["policy"]["source_ref"]]
                    + [case["source_ref"] for case in state["catalog"]]))}

    def plan_tests(self, state):
        if state.get("error"):
            return {}
        saved = self.planner.decide(state["project_id"], state["cycle_id"], self.planner_context(state), state["memory_enabled"])
        return {"planner_decision_id": saved["id"], "planner_decision": saved["plan"], "error": saved["error"]}

    def validate_plan(self, state):
        if state.get("error"):
            return {"next_action": "needs_review"}
        plan = validate_decision(state["planner_decision"], self.planner_context(state))
        return {"selected_test_ids": plan.test_ids, "next_action": "run_tests" if plan.decision == "RUN_TESTS"
                else plan.decision.lower(), "pending_approval": True}

    def run_tests(self, state):
        prompt = self._prompt(state)
        catalog = {case["test_id"]: case for case in state["catalog"]}
        results = []
        for key in state["selected_test_ids"]:
            try:
                result = self.executor.execute_llm_test(state["project_id"], state["cycle_id"], catalog[key]["id"],
                        f"graph:{state['cycle_id']}:{catalog[key]['id']}", prompt, self.settings)
            except (ExecutionError, ProviderError) as exc:
                return {"execution_results": results, "error": exc.code}
            results.append({"test_id": key, "case_id": catalog[key]["id"], "execution_id": result["execution_id"],
                            "status": result["status"], "validation": result["validation"]})
        return {"execution_results": results}

    def validate_outputs(self, state):
        # Revalidate durable outputs against the cycle's pinned policy and case.
        with Repository(self.db_path) as store:
            for result in state["execution_results"]:
                row = store.get_test_execution(state["project_id"], result["execution_id"])
                case = store.get_test_case(state["project_id"], result["case_id"])
                tags = json.loads(case["tags_json"])
                evaluation = SettlementEvaluator(case["input_text"], json.loads(case["expected_json"]), state["policy"]["rules"],
                             ambiguous="ambiguous" in tags, unsupported_unit="ambiguous" in tags and "unit" in tags)
                checked = evaluation.evaluate(json.loads(row["response_json"])["raw_text"]).model_dump()
                if row["cycle_id"] != state["cycle_id"] or checked != result["validation"]:
                    raise ValueError("durable_validation_mismatch")
        return {}

    def reconcile_failures(self, state):
        if state.get("error"):
            return {"risk_changes": []}
        changes = []
        with Repository(self.db_path) as store:
            risks = store.get_open_risks(state["project_id"])
        for result in state["execution_results"]:
            evidence = {"case_id": result["case_id"], "test_id": result["test_id"], "execution_id": result["execution_id"],
                        "discrepancies": result["validation"]["discrepancies"]}
            if result["status"] == "fail":
                changes.append({"action": "record", "fingerprint": f"case:{result['case_id']}",
                                "category": next((case["tags"][0] for case in state["catalog"] if case["id"] == result["case_id"]),
                                                 "extraction"), "evidence": evidence})
            elif result["status"] == "pass":
                for risk in risks:
                    if json.loads(risk["evidence_json"]).get("case_id") == result["case_id"]:
                        changes.append({"action": "resolve", "risk_id": risk["id"], "evidence": evidence})
        return {"risk_changes": changes}

    def write_memory_and_audit(self, state):
        # Each domain write commits with its audit event. Re-entry skips that exact
        # cycle/evidence even if the process died before its next checkpoint.
        p, c = state["project_id"], state["cycle_id"]
        with Repository(self.db_path) as store:
            for change in state["risk_changes"]:
                with read_snapshot(self.db_path) as db:
                    row = db.execute("SELECT * FROM failure_memories WHERE project_id=? AND " +
                                     ("fingerprint=?" if change["action"] == "record" else "id=?"),
                                     (p, change.get("fingerprint", change.get("risk_id")))).fetchone()
                if row and row["last_cycle_id"] == c and json.loads(row["evidence_json"]) == change["evidence"]:
                    continue
                if change["action"] == "record":
                    store.record_failure(p, c, change["fingerprint"], change["category"], change["evidence"])
                elif row and row["status"] != "resolved":
                    store.resolve_failure(p, change["risk_id"], c, change["evidence"])
        self._once(state, "graph_memory_written", {"risk_changes": state["risk_changes"],
                   "selected": state["selected_test_ids"], "executed": [r["test_id"] for r in state["execution_results"]]})
        return {}

    def prepare_recommendation(self, state):
        p, c = state["project_id"], state["cycle_id"]
        with Repository(self.db_path) as store:
            risks = store.get_open_risks(p)
            rejected = any(row["prompt_version_id"] == state["version_id"] and row["decision"] == "rejected"
                           for row in store.get_human_decisions(p))
            results = state["execution_results"]
            complete = bool(results) and len(results) == len(state["selected_test_ids"]) and not state.get("error")
            action = "needs_review"
            if complete and any(row["status"] == "fail" for row in results):
                action = "revise"
            elif complete and all(row["status"] == "pass" for row in results) and not risks and not rejected:
                action = "promote_candidate"
            recommendation = {"action": action, "approval": "pending", "planner_action": state.get("next_action"),
                              "error": state.get("error"), "results": results, "open_risk_ids": [r["id"] for r in risks],
                              "prior_rejection": rejected, "source_refs": state.get("git_evidence", {}).get("source_refs", []),
                              "planner_decision_id": state.get("planner_decision_id")}
            cycle = store.get_review_cycle(p, c)
            target = "completed" if complete else "needs_review"
            if cycle["status"] != target:
                store.transition_cycle(p, c, target)
        self._once(state, "graph_recommendation", recommendation)
        return {"recommendation": recommendation, "next_action": action, "pending_approval": True}
