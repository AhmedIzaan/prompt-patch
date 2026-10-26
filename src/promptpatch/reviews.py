"""CLI review controller; immutable request metadata makes resume reproducible."""

import json
from pathlib import Path

from promptpatch.errors import RecordNotFound, SupersededPolicy
from promptpatch.evaluator import SettlementEvaluator
from promptpatch.git_tool import GitEvidenceTool, RepositoryAccess
from promptpatch.graph import ReviewGraph
from promptpatch.model_provider import GeminiProvider, ModelSettings, ReplayProvider
from promptpatch.repository import Repository, digest, utc_now
from promptpatch.review_audit import CycleGitTools, CycleMemoryTools
from promptpatch.tool_support import read_snapshot


class ReviewError(ValueError):
    """Safe, actionable controller error; messages never contain source values."""


def version_by_label(db_path, project_id, label):
    with Repository(db_path) as store:
        store.get_project(project_id)
    with read_snapshot(db_path) as db:
        row = db.execute("SELECT * FROM prompt_versions WHERE project_id=? AND label=?", (project_id, label)).fetchone()
    if not row:
        raise RecordNotFound("Prompt version not found in this project.")
    return dict(row)


def cycle_by_key(db_path, project_id, key):
    with Repository(db_path) as store:
        store.get_project(project_id)
    with read_snapshot(db_path) as db:
        row = db.execute("SELECT * FROM review_cycles WHERE project_id=? AND cycle_key=?", (project_id, key)).fetchone()
    if not row:
        raise RecordNotFound("Review cycle not found in this project.")
    return dict(row)


def saved_request(db_path, project_id, cycle_id):
    with read_snapshot(db_path) as db:
        row = db.execute("SELECT details_json FROM audit_events WHERE project_id=? AND cycle_id=? "
                         "AND event_type='review_requested' ORDER BY created_at LIMIT 1", (project_id, cycle_id)).fetchone()
    if not row:
        raise ReviewError("No CLI request saved for this cycle; use its original integration entry point.")
    return json.loads(row[0])


class CursorReplayProvider(ReplayProvider):
    """Restore a labeled replay stream to its persisted model-call position.

    Advancing fixture events is not a model call and produces no new audit event.
    Unknown in-flight operations still fail closed inside planner/executor.
    """
    def __init__(self, path, scenario, consumed):
        super().__init__(path, scenario)
        for _ in range(consumed):
            if next(self._events, None) is None:
                raise ReviewError("Replay history exceeds the fixture event count.")


class ReviewRepository(Repository):
    """Add a CLI request and cycle in the same domain transaction."""
    def create_requested_cycle(self, project_id, key, version_id, policy_id, request):
        with self._transaction():
            self._project(project_id, writable=True)
            self.get_prompt_version(project_id, version_id)
            if self.get_active_policy(project_id)["id"] != policy_id:
                raise SupersededPolicy("Policy changed during preflight; start a new review under the current policy.")
            identity = self._insert("review_cycles", project_id=project_id, cycle_key=key,
                                    prompt_version_id=version_id, policy_id=policy_id, status="pending", created_at=utc_now())
            self._audit(project_id, "cycle_created", identity, {}, identity)
            self._audit(project_id, "review_requested", identity, request, identity)
        return self.get_review_cycle(project_id, identity)


class Reviews:
    def __init__(self, settings):
        self.settings = settings
        self.db_path = settings.db_path

    def _git(self, project_id, prompt_path, cycle_id=None):
        # Trusted local CLI configuration, never a path supplied by the planner.
        tool = (CycleGitTools if cycle_id else GitEvidenceTool)(self.db_path, {project_id: RepositoryAccess(
            self.settings.demo_repo, frozenset({prompt_path}))})
        if cycle_id:
            tool.cycle_id = cycle_id
        return tool

    def _provider(self, request, project_id=None, cycle_id=None):
        if request["mode"] != self.settings.mode:
            raise ReviewError("Configured mode differs from this review; restore the original mode to resume.")
        if request["mode"] == "live":
            if not self.settings.gemini_api_key:
                raise ReviewError("Set GEMINI_API_KEY in the local process environment before starting or resuming.")
            return GeminiProvider(self.settings.gemini_api_key)
        path = Path(request["replay_file"])
        if path.stat().st_size > 262144 or digest(path.read_text()) != request["replay_hash"]:
            raise ReviewError("Replay fixture changed or exceeds 256 KiB; restore the original fixture.")
        consumed = 0
        if cycle_id:
            with read_snapshot(self.db_path) as db:
                consumed = db.execute("SELECT COUNT(*) FROM audit_events WHERE project_id=? AND cycle_id=? "
                                      "AND event_type='model_call_started'", (project_id, cycle_id)).fetchone()[0]
        return CursorReplayProvider(path, request["replay_scenario"], consumed)

    def _prerequisites(self, project_id, version, base, policy):
        if self.db_path.resolve() == self.settings.checkpoint_db_path.resolve():
            raise ReviewError("Domain and checkpoint databases must be separate.")
        with Repository(self.db_path) as store:
            if store.get_project(project_id)["archived_at"] or version["status"] != "candidate":
                raise ReviewError("Project or prompt version is archived.")
            cases = store.get_active_test_cases(project_id)
        rules = json.loads(policy["rules_json"])
        if not isinstance(rules, dict):
            raise ReviewError("Approved policy must contain an object of rules.")
        allowed, required, budget = rules.get("allowed_test_ids"), rules.get("required_test_ids"), rules.get("max_tests_per_review")
        if (not isinstance(allowed, list) or not allowed or any(not isinstance(k, str) for k in allowed)
                or not isinstance(required, list) or not required or any(not isinstance(k, str) for k in required)
                or type(budget) is not int or not len(set(required)) <= budget <= 12):
            raise ReviewError("Approved testing policy has invalid IDs or budget.")
        catalog = {row["case_key"]: row for row in cases}
        if not set(required) <= set(allowed) <= set(catalog):
            raise ReviewError("Approved policy references missing active cases; correct the policy or cases first.")
        if len(allowed) > 50:
            raise ReviewError("Active catalog exceeds the graph budget.")
        for key in allowed:
            case = catalog[key]
            tags, expected = json.loads(case["tags_json"]), json.loads(case["expected_json"])
            if digest({"input": case["input_text"], "expected": expected, "tags": tags}) != case["content_hash"]:
                raise ReviewError("Stored reference identity mismatch; review the source before execution.")
            SettlementEvaluator(case["input_text"], expected, rules, ambiguous="ambiguous" in tags,
                                unsupported_unit="ambiguous" in tags and "unit" in tags)
        git = self._git(project_id, version["prompt_path"])
        git.read_git_prompt(project_id, version["git_commit_sha"], version["prompt_path"])
        if base:
            git.compare_prompt_versions(project_id, base["git_commit_sha"], version["git_commit_sha"], version["prompt_path"])
        return git

    def start(self, project_id, label, key, *, base_label=None, memory_enabled=True,
              replay_file=None, replay_scenario=None, timeout_ms=20000):
        if not key.strip() or len(key) > 128:
            raise ReviewError("Cycle key must contain 1–128 characters.")
        version = version_by_label(self.db_path, project_id, label)
        base = version_by_label(self.db_path, project_id, base_label) if base_label else None
        model_id = self.settings.gemini_model if self.settings.mode == "live" else "module07-replay"
        if not model_id:
            raise ReviewError("Set GEMINI_MODEL in the local process environment.")
        model = ModelSettings(model_id=model_id, timeout_ms=timeout_ms)
        if self.settings.mode == "replay" and (not replay_file or not replay_scenario):
            raise ReviewError("Replay mode requires --replay-file and --replay-scenario; it is never a live fallback.")
        if self.settings.mode == "live" and (replay_file or replay_scenario):
            raise ReviewError("Replay arguments require PROMPTPATCH_MODE=replay.")
        request = {"version_id": version["id"], "base_version_id": base["id"] if base else None,
                   "memory_enabled": memory_enabled, "mode": self.settings.mode, "model": model.model_dump(),
                   "replay_file": str(Path(replay_file).resolve()) if replay_file else None,
                   "replay_scenario": replay_scenario, "replay_hash": None}
        if replay_file:
            path = Path(replay_file)
            if path.stat().st_size > 262144:
                raise ReviewError("Replay fixture exceeds 256 KiB.")
            request["replay_hash"] = digest(path.read_text())
        # Configuration/fixture preflight makes no external request.
        self._provider(request)
        try:
            existing = cycle_by_key(self.db_path, project_id, key)
        except RecordNotFound:
            existing = None
        if existing:
            old = saved_request(self.db_path, project_id, existing["id"])
            if old != request:
                raise ReviewError("Cycle already exists with different inputs; resume it or choose a new cycle key.")
            return self.resume(project_id, key)
        with Repository(self.db_path) as store:
            policy = store.get_active_policy(project_id)
        self._prerequisites(project_id, version, base, policy)
        with ReviewRepository(self.db_path) as store:
            store.create_requested_cycle(project_id, key, version["id"], policy["id"], request)
        return self.resume(project_id, key)

    def resume(self, project_id, key):
        cycle = cycle_by_key(self.db_path, project_id, key)
        request = saved_request(self.db_path, project_id, cycle["id"])
        with Repository(self.db_path) as store:
            version = store.get_prompt_version(project_id, cycle["prompt_version_id"])
            if request["version_id"] != version["id"]:
                raise ReviewError("Saved request does not match the cycle version.")
            if request["base_version_id"]:
                store.get_prompt_version(project_id, request["base_version_id"])
        provider = self._provider(request, project_id, cycle["id"])
        graph = ReviewGraph(self.db_path, self.settings.checkpoint_db_path, self._git(project_id, version["prompt_path"], cycle["id"]),
                            provider, ModelSettings(**request["model"]))
        graph.memory = CycleMemoryTools(self.db_path)
        graph.memory.cycle_id = cycle["id"]
        try:
            graph.run(project_id, cycle["id"], memory_enabled=request["memory_enabled"], base_version_id=request["base_version_id"])
        except ValueError as exc:
            if str(exc) == "nonpending_cycle_without_checkpoint":
                raise ReviewError("Review checkpoint is missing; restore its original checkpoint database before resuming.") from None
            if str(exc) == "checkpoint_request_changed":
                raise ReviewError("Checkpoint inputs differ; restore the original configuration before resuming.") from None
            raise
        return self.status(project_id, key)

    def status(self, project_id, key):
        cycle = cycle_by_key(self.db_path, project_id, key)
        with Repository(self.db_path) as store:
            version = store.get_prompt_version(project_id, cycle["prompt_version_id"])
            policy = store.get_policy(project_id, cycle["policy_id"])
        with read_snapshot(self.db_path) as db:
            plan = db.execute("SELECT * FROM planner_decisions WHERE project_id=? AND cycle_id=?", (project_id, cycle["id"])).fetchone()
            executions = db.execute("SELECT e.*,t.case_key FROM test_executions e JOIN test_cases t ON t.project_id=e.project_id "
                                    "AND t.id=e.test_case_id WHERE e.project_id=? AND e.cycle_id=? ORDER BY e.created_at,e.id",
                                    (project_id, cycle["id"])).fetchall()
            event = db.execute("SELECT details_json FROM audit_events WHERE project_id=? AND cycle_id=? "
                               "AND event_type='graph_recommendation' ORDER BY created_at DESC LIMIT 1", (project_id, cycle["id"])).fetchone()
            human = db.execute("SELECT * FROM human_decisions WHERE project_id=? AND cycle_id=?", (project_id, cycle["id"])).fetchone()
            failures = db.execute("SELECT event_type,details_json,created_at FROM audit_events WHERE project_id=? AND cycle_id=? "
                                  "AND (event_type LIKE '%failed' OR event_type LIKE 'graph_node_%') ORDER BY created_at",
                                  (project_id, cycle["id"])).fetchall()
        payload = json.loads(plan["decision_json"]) if plan else None
        parsed = payload.get("plan") if payload else None
        recommendation = json.loads(event[0]) if event else None
        return {"project_id": project_id, "version": version["label"], "version_id": version["id"],
                "cycle": key, "cycle_id": cycle["id"], "status": cycle["status"], "policy_id": policy["id"],
                "policy_revision": policy["revision"], "policy_status": policy["status"],
                "mode": payload["response"]["mode"] if payload and payload.get("response") else None,
                "planner": parsed, "planner_error": payload.get("error") if payload else None,
                "selected_test_ids": parsed.get("test_ids", []) if isinstance(parsed, dict) and not payload.get("error") else [],
                "supplied_memory_refs": payload.get("supplied_memory_refs", []) if payload else [],
                "source_refs": payload["input"]["source_refs"] if payload else [],
                "results": [{"execution_id": r["id"], "test_id": r["case_key"], "status": r["status"],
                             "validation": json.loads(r["validation_json"]), "elapsed_ms": r["elapsed_ms"]} for r in executions],
                "recommendation": recommendation, "next_action": recommendation["action"] if recommendation else "resume_review",
                "approval": human["decision"] if human else "pending", "human_decision": dict(human) if human else None,
                "errors": [{"event_type": r["event_type"], **json.loads(r["details_json"]), "created_at": r["created_at"]}
                           for r in failures if json.loads(r["details_json"]).get("error") or "failed" in r["event_type"]]}
