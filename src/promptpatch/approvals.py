"""Explicit local owner actions; source/model text cannot call these services."""
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from promptpatch.errors import DuplicateOperation, InvalidStateTransition, RecordNotFound
from promptpatch.evaluator import EvaluationRules, SettlementEvaluator, parse_json
from promptpatch.repository import Repository
from promptpatch.reviews import cycle_by_key, version_by_label, ReviewError
from promptpatch.tool_support import read_snapshot


class PolicyDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    revision: int = Field(ge=1)
    status: str
    description: str = Field(min_length=1, max_length=2000)
    rules: dict[str, JsonValue]


def validate_policy(store, project_id, rules):
    EvaluationRules.model_validate(rules)
    allowed, required, budget = rules.get("allowed_test_ids"), rules.get("required_test_ids"), rules.get("max_tests_per_review")
    if (not isinstance(allowed, list) or not allowed or any(not isinstance(k, str) for k in allowed)
            or not isinstance(required, list) or not required or any(not isinstance(k, str) for k in required)
            or type(budget) is not int or not len(set(required)) <= budget <= 12
            or len(set(allowed)) != len(allowed) or len(set(required)) != len(required)):
        raise ReviewError("Policy needs unique allowed/required test IDs and a valid test budget.")
    cases = {r["case_key"]: r for r in store.get_active_test_cases(project_id)}
    if not set(required) <= set(allowed) <= set(cases):
        raise ReviewError("Policy IDs must match this project's active cases.")
    if rules.get("source_instructions") != "untrusted_data_only":
        raise ReviewError("Source content must remain untrusted data.")
    for key in allowed:
        case = cases[key]
        tags = json.loads(case["tags_json"])
        SettlementEvaluator(case["input_text"], json.loads(case["expected_json"]), rules,
                            ambiguous="ambiguous" in tags, unsupported_unit="ambiguous" in tags and "unit" in tags)


def propose_policy(db_path, project_id, path, *, actor, reason):
    path = Path(path)
    if path.stat().st_size > 65536:
        raise ReviewError("Policy file exceeds 64 KiB.")
    document = PolicyDocument.model_validate(parse_json(path.read_text()))
    with Repository(db_path) as store:
        validate_policy(store, project_id, document.rules)
        with read_snapshot(db_path) as db:
            revision = db.execute("SELECT COALESCE(MAX(revision),0)+1 FROM evaluation_policies WHERE project_id=?",
                                  (project_id,)).fetchone()[0]
        if document.revision != revision:
            raise ReviewError("Policy file revision must equal this project's next revision.")
        return store.propose_policy_revision(project_id, document.rules, actor=actor, reason=reason)


def approve_policy(db_path, project_id, revision, *, actor):
    with Repository(db_path) as store:
        store.get_project(project_id)
        with read_snapshot(db_path) as db:
            row = db.execute("SELECT * FROM evaluation_policies WHERE project_id=? AND revision=?", (project_id, revision)).fetchone()
        if not row:
            raise RecordNotFound("Policy revision not found in this project.")
        validate_policy(store, project_id, json.loads(row["rules_json"]))
        return store.approve_policy_revision(project_id, row["id"], actor=actor)


def decide_version(db_path, project_id, label, cycle_key, decision, *, actor, comments=""):
    version = version_by_label(db_path, project_id, label)
    cycle = cycle_by_key(db_path, project_id, cycle_key)
    if cycle["prompt_version_id"] != version["id"]:
        raise InvalidStateTransition("Version must match the explicitly selected review cycle.")
    with Repository(db_path) as store:
        with read_snapshot(db_path) as db:
            prior = db.execute("SELECT 1 FROM human_decisions WHERE project_id=? AND cycle_id=?", (project_id, cycle["id"])).fetchone()
            event = db.execute("SELECT details_json FROM audit_events WHERE project_id=? AND cycle_id=? "
                               "AND event_type='graph_recommendation' ORDER BY created_at DESC LIMIT 1", (project_id, cycle["id"])).fetchone()
        if prior:
            raise DuplicateOperation("This review already has an immutable human decision.")
        if decision == "approved":
            recommendation = json.loads(event[0]) if event else {}
            if (cycle["status"] != "completed" or recommendation.get("action") != "promote_candidate"
                    or store.get_open_risks(project_id)
                    or store.get_active_policy(project_id)["id"] != cycle["policy_id"]):
                raise InvalidStateTransition("Approval requires a completed promotion candidate under the current policy with no open risks.")
        return store.add_human_decision(project_id, version["id"], cycle["id"], decision, actor=actor, comments=comments)
