"""Read-only, project-scoped measurements from authoritative records.

Started calls include failed/unknown attempts. Results and provider responses are
counted once from immutable rows, even if the trailing audit event was interrupted.
No provider prices or missing token counts are guessed.
"""
import json
from collections import Counter
from pathlib import Path

from promptpatch.repository import Repository
from promptpatch.security import redact
from promptpatch.tool_support import read_snapshot

TOKEN_FIELDS = ("prompt_token_count", "candidates_token_count", "thoughts_token_count", "total_token_count")


def review_telemetry(db_path, project_id, cycle_id, *, checkpoint_path=None):
    with Repository(db_path) as store:
        cycle = store.get_review_cycle(project_id, cycle_id)
    with read_snapshot(db_path) as db:
        events = [dict(row) for row in db.execute("SELECT * FROM audit_events WHERE project_id=? AND cycle_id=? ORDER BY created_at,rowid",
                                                (project_id, cycle_id))]
        executions = [dict(row) for row in db.execute("SELECT * FROM test_executions WHERE project_id=? AND cycle_id=? ORDER BY created_at,id", (project_id, cycle_id))]
        planners = [dict(row) for row in db.execute("SELECT * FROM planner_decisions WHERE project_id=? AND cycle_id=?", (project_id, cycle_id))]
        attempts = [dict(row) for row in db.execute("SELECT a.* FROM operation_attempts a JOIN tool_operations o ON o.project_id=a.project_id AND o.id=a.operation_id "
                                                  "WHERE a.project_id=? AND o.cycle_id=? ORDER BY a.created_at,a.id", (project_id, cycle_id))]
        duplicate_results = db.execute("SELECT COALESCE(SUM(n-1),0) FROM (SELECT COUNT(*) n FROM test_executions "
                                       "WHERE project_id=? AND cycle_id=? GROUP BY operation_key HAVING n>1)", (project_id, cycle_id)).fetchone()[0]
        duplicate_decisions = db.execute("SELECT MAX(COUNT(*)-1,0) FROM human_decisions WHERE project_id=? AND cycle_id=?", (project_id, cycle_id)).fetchone()[0]
    decoded = [{**row, "details": json.loads(row["details_json"])} for row in events]
    started = [r for r in decoded if r["event_type"] == "model_call_started"]
    failed = [r for r in decoded if r["event_type"] == "model_call_failed"]
    responses = [json.loads(row["response_json"]) for row in executions]
    logical_latencies = [row["elapsed_ms"] for row in executions]
    missing_planner_latency = 0
    for row in planners:
        value = json.loads(row["decision_json"])
        if value.get("response"):
            responses.append(value["response"])
        latency = value.get("elapsed_ms")
        if latency is None and value.get("response"):
            latency = value["response"].get("elapsed_ms")
        if latency is None:
            missing_planner_latency += 1
        else:
            logical_latencies.append(latency)
    tokens, unknown = {}, {}
    for field in TOKEN_FIELDS:
        known = [r.get("usage", {}).get(field) for r in responses if type(r.get("usage", {}).get(field)) is int]
        tokens[field] = sum(known) if known else None
        unknown[field] = len(responses) - len(known)
    model_modes = {r.get("mode") for r in responses}
    failure_details = [{"purpose": r["details"].get("purpose"), "error_code": r["details"].get("error_code"),
                        "http_status": r["details"].get("http_status"), "timeout": r["details"].get("timeout"),
                        "elapsed_ms": r["details"].get("elapsed_ms")} for r in failed]
    call_counts = Counter(r["ref_id"] for r in started)
    attempt_counts = Counter(row["operation_id"] for row in attempts)
    return redact({"project_id": project_id, "cycle_id": cycle_id, "cycle_status": cycle["status"],
        "MODEL_CALLS": len(started), "LIVE_MODEL_CALLS": sum(r["details"].get("mode") == "live" for r in started),
        "MODEL_CALLS_BY_PURPOSE": {purpose: sum(r["details"].get("purpose") == purpose for r in started)
                                   for purpose in ("planner", "candidate_execution")},
        "RECEIVED_PROVIDER_RESPONSES": len(responses), "FAILED_MODEL_CALLS": len(failed),
        "UNKNOWN_INFLIGHT_OPERATIONS": sum(count > attempt_counts[operation] for operation, count in call_counts.items()),
        "LOGICAL_LATENCY_MS": sum(logical_latencies), "MISSING_PLANNER_LATENCY_RECORDS": missing_planner_latency,
        "PROVIDER_RESPONSE_LATENCY_MS": sum(r.get("elapsed_ms", 0) for r in responses),
        "ATTEMPT_LATENCY_MS": sum(json.loads(r["details_json"]).get("elapsed_ms", 0) for r in attempts),
        "MISSING_ATTEMPT_LATENCY_RECORDS": sum("elapsed_ms" not in json.loads(r["details_json"]) for r in attempts),
        "latency_note": "Observed sums, not end-to-end wall time; old missing failure timings remain unknown.",
        "TOKEN_USAGE": tokens, "TOKEN_USAGE_UNKNOWN_RESPONSES": unknown,
        "provider_modes": sorted(v for v in model_modes if v), "failure_details": failure_details,
        "COMPLETED_TESTS": len(executions), "DUPLICATE_ACTIONS": duplicate_results + duplicate_decisions,
        "call_status_note": "Received responses can contain invalid plans. Failed-call audit events include output-validation failures; neither proves successful agency.",
        "duplicate_definition": "Extra completed results per operation key plus extra human decisions per cycle; not HTTP exactly-once billing.",
        "APPROXIMATE_COST": None, "cost_note": "No verified price configured; replay has no measured provider tokens/cost.",
        "LOCAL_STORAGE_BYTES": {"domain": Path(db_path).stat().st_size,
             "checkpoint": Path(checkpoint_path).stat().st_size if checkpoint_path and Path(checkpoint_path).exists() else None}})
