"""Execute one registered case with bounded, auditable provider attempts.

Sequential replay of a completed operation returns its saved result. Unfinished
external attempts fail closed on resume: provider-side exactly-once billing is
not promised. Concurrent workers are outside this single-agent module's scope.
"""

import hashlib
import json
from pathlib import Path
from time import perf_counter, sleep

from promptpatch.errors import RecordNotFound
from promptpatch.evaluator import EvaluationConfigError, SettlementEvaluator
from promptpatch.model_provider import ModelSettings, ProviderError
from promptpatch.models import SettlementExtraction
from promptpatch.repository import Repository, digest
from promptpatch.tool_support import read_snapshot


class ExecutionError(RuntimeError):
    def __init__(self, code):
        super().__init__("Test execution requires review: " + code)
        self.code = code


class TestExecutor:
    __test__ = False  # This application class is not a pytest test container.

    def __init__(self, db_path: Path, provider):
        self.db_path, self.provider = Path(db_path), provider

    @staticmethod
    def _result(row, *, reused):
        response = json.loads(row["response_json"])
        return {"execution_id": row["id"], "project_id": row["project_id"], "status": row["status"],
                "validation": json.loads(row["validation_json"]), "response": response,
                "elapsed_ms": row["elapsed_ms"], "reused": reused}

    def execute_llm_test(self, project_id, cycle_id, test_case_id, operation_key,
                         prompt_snapshot, model_settings: ModelSettings):
        with Repository(self.db_path) as store:
            cycle = store.get_review_cycle(project_id, cycle_id)
            prompt = store.get_prompt_version(project_id, cycle["prompt_version_id"])
            case = store.get_test_case(project_id, test_case_id)
            policy = store.get_policy(project_id, cycle["policy_id"])
            if (prompt_snapshot.project_id != project_id or prompt_snapshot.prompt_version_id != prompt["id"]
                    or prompt_snapshot.commit_sha != prompt["git_commit_sha"]
                    or prompt_snapshot.prompt_relpath != prompt["prompt_path"]
                    or prompt_snapshot.content_hash != prompt["content_hash"]
                    or hashlib.sha256(prompt_snapshot.content.encode()).hexdigest() != prompt["content_hash"]):
                raise ExecutionError("prompt_identity_mismatch")
            rules, expected, tags = json.loads(policy["rules_json"]), json.loads(case["expected_json"]), json.loads(case["tags_json"])
            if digest({"input": case["input_text"], "expected": expected, "tags": tags}) != case["content_hash"]:
                raise ExecutionError("reference_identity_mismatch")
            if policy["status"] not in {"approved", "superseded"}:
                raise ExecutionError("policy_not_approved")
            request_hash = digest({"cycle_id": cycle_id, "prompt_version_id": prompt["id"],
                                   "prompt_hash": prompt["content_hash"], "case_id": case["id"],
                                   "case_hash": case["content_hash"], "policy_id": policy["id"],
                                   "provider": self.provider.name, "mode": self.provider.mode,
                                   "purpose": "candidate_execution", "settings": model_settings.model_dump()})
            try:
                operation = store.get_tool_operation(project_id, operation_key)
            except RecordNotFound:
                operation = None
            if operation is not None:
                if (operation["request_hash"] != request_hash or operation["cycle_id"] != cycle_id
                        or operation["tool"] != "execute_llm_test"):
                    raise ExecutionError("operation_request_mismatch")
                if operation["status"] == "completed":
                    return self._result(store.get_test_execution(project_id, operation["result_ref"]), reused=True)
            if not case["active"] or cycle["status"] == "completed":
                raise ExecutionError("inactive_case_or_completed_cycle")
            if len(prompt_snapshot.content.encode()) > 65536 or len(case["input_text"].encode()) > 65536:
                raise ExecutionError("input_limit")
            allowed, budget = rules.get("allowed_test_ids"), rules.get("max_tests_per_review")
            if (not isinstance(allowed, list) or case["case_key"] not in allowed
                    or type(budget) is not int or not 1 <= budget <= 12):
                raise ExecutionError("case_or_budget_not_allowed")
            with read_snapshot(self.db_path) as connection:
                metadata = connection.execute(
                    "SELECT details_json FROM audit_events WHERE project_id=? AND ref_id=? "
                    "AND event_type='fixture_case_imported' ORDER BY created_at DESC LIMIT 1",
                    (project_id, case["id"]),
                ).fetchone()
                existing_count = connection.execute(
                    "SELECT COUNT(*) FROM tool_operations WHERE project_id=? AND cycle_id=? AND tool='execute_llm_test'",
                    (project_id, cycle_id),
                ).fetchone()[0]
            ambiguous = "ambiguous" in tags or (metadata is not None and
                        json.loads(metadata[0]).get("expected_status") == "needs_clarification")
            evaluator = SettlementEvaluator(case["input_text"], expected, rules, ambiguous=ambiguous,
                                            unsupported_unit=ambiguous and "unit" in tags)
            if operation is None:
                if existing_count >= budget:
                    raise ExecutionError("cycle_test_budget_exhausted")
                operation = store.begin_tool_operation(project_id, cycle_id, operation_key,
                                                       "execute_llm_test", request_hash)
            attempts = store.get_operation_attempts(project_id, operation_key)
            with read_snapshot(self.db_path) as connection:
                started_count = connection.execute(
                    "SELECT COUNT(*) FROM audit_events WHERE project_id=? AND cycle_id=? AND ref_id=? "
                    "AND event_type='model_call_started'", (project_id, cycle_id, operation["id"]),
                ).fetchone()[0]
            if started_count > len(attempts):
                raise ExecutionError("interrupted_provider_attempt")
            if started_count >= model_settings.max_attempts:
                raise ExecutionError("provider_attempt_budget_exhausted")
            if attempts and not json.loads(attempts[-1]["details_json"]).get("retryable", False):
                raise ExecutionError("previous_failure_not_retryable")
            prior_elapsed = sum(json.loads(row["details_json"]).get("elapsed_ms", 0) for row in attempts)
            run_started = perf_counter()
            for attempt in range(started_count + 1, model_settings.max_attempts + 1):
                metadata = {"purpose": "candidate_execution", "provider": self.provider.name,
                            "mode": self.provider.mode, "model_id": model_settings.model_id, "attempt": attempt}
                store.append_audit_event(project_id, "model_call_started", operation["id"], metadata, cycle_id)
                attempt_started = perf_counter()
                try:
                    response = self.provider.generate_once(prompt_snapshot.content, case["input_text"], model_settings,
                                                           purpose="candidate_execution",
                                                           response_schema=SettlementExtraction.model_json_schema())
                    if (response.purpose != "candidate_execution" or response.provider != self.provider.name
                            or response.mode != self.provider.mode or response.model_id != model_settings.model_id):
                        raise ProviderError("provider_identity_mismatch")
                    if len(response.raw_text.encode()) > 65536:
                        raise ProviderError("response_limit")
                except ProviderError as error:
                    elapsed = (perf_counter() - attempt_started) * 1000
                    details = {**metadata, "error_code": error.code, "timeout": error.timed_out,
                               "elapsed_ms": elapsed, "retryable": error.retryable}
                    store.finish_tool_operation(project_id, operation_key, success=False, details=details)
                    store.append_audit_event(project_id, "model_call_failed", operation["id"], details, cycle_id)
                    if not error.retryable or attempt == model_settings.max_attempts:
                        raise
                    sleep(0.2)
                    continue
                validation = evaluator.evaluate(response.raw_text)
                payload = {**response.model_dump(), "parsed_json": validation.parsed_json,
                           "request_hash": request_hash, "policy_id": policy["id"], "test_case_id": case["id"],
                           "prompt_version_id": prompt["id"], "approximate_cost": None}
                row = store.record_test_execution(
                    project_id, cycle_id, case["id"], operation_key, provider=response.provider,
                    model_id=response.model_id, response=payload, validation=validation.model_dump(),
                    status=validation.status, elapsed_ms=prior_elapsed + (perf_counter() - run_started) * 1000,
                )
                store.append_audit_event(project_id, "model_call_completed", operation["id"], {
                    **metadata, "execution_id": row["id"], "elapsed_ms": response.elapsed_ms,
                    "usage": response.usage, "live_model_calls": 1 if response.mode == "live" else 0,
                }, cycle_id)
                return self._result(row, reused=False)
        raise ExecutionError("no_provider_attempt")
