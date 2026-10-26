"""Project-scoped domain memory. Mutations and their audit events commit together.

Rows are returned as dictionaries; *_json columns contain canonical JSON strings.
The public API exposes no arbitrary SQL/table names and no history deletion.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from promptpatch.db import SCHEMA_VERSION, connect
from promptpatch.security import contains_credentials, redact
from promptpatch.errors import (
    DuplicateOperation, InvalidStateTransition, RecordNotFound, StoreError, SupersededPolicy,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(encode(value).encode()).hexdigest()


class Repository:
    def __init__(self, path: Path):
        self._db = connect(Path(path))
        if self._db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            self._db.close()
            raise StoreError("Initialize a supported domain database first.")

    def close(self):
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @contextmanager
    def _transaction(self):
        try:
            self._db.execute("BEGIN IMMEDIATE")
            yield
            self._db.commit()
        except sqlite3.IntegrityError as exc:
            self._db.rollback()
            if "UNIQUE constraint" in str(exc):
                raise DuplicateOperation("Logical action or immutable identity already exists.") from None
            raise StoreError("Database constraint rejected the operation.") from None
        except BaseException:
            self._db.rollback()
            raise

    @staticmethod
    def _safe(value):
        if contains_credentials(value):
            raise StoreError("Credential material cannot be persisted; use an explicit owner correction.")

    def _insert(self, table: str, **values) -> str:
        # Table/column identifiers come exclusively from internal constant callers.
        values = {"id": str(uuid4()), **values}
        self._safe(values)
        columns = ",".join(values)
        placeholders = ",".join("?" for _ in values)
        self._db.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values()))
        return values["id"]

    def _get(self, table: str, project_id: str, record_id: str) -> dict:
        row = self._db.execute(
            f"SELECT * FROM {table} WHERE project_id=? AND id=?", (project_id, record_id)
        ).fetchone()
        if row is None:
            raise RecordNotFound("Record not found in this project.")
        return dict(row)

    def _project(self, project_id: str, *, writable=False) -> dict:
        row = self._db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise RecordNotFound("Project not found.")
        if writable and row["archived_at"] is not None:
            raise InvalidStateTransition("Project is archived.")
        return dict(row)

    def _audit(self, project_id, event_type, ref_id, details, cycle_id=None):
        return self._insert(
            "audit_events", project_id=project_id, cycle_id=cycle_id, event_type=event_type,
            ref_id=ref_id, details_json=encode(redact(details)), created_at=utc_now(),
        )

    @staticmethod
    def _actor(actor):
        if not isinstance(actor, str) or not actor.strip():
            raise InvalidStateTransition("Explicit nonempty actor required.")
        Repository._safe(actor)

    def create_project(self, project_id: str, name: str) -> dict:
        if not project_id.strip() or not name.strip():
            raise InvalidStateTransition("Project identifier and name are required.")
        with self._transaction():
            self._insert("projects", id=project_id, name=name, created_at=utc_now())
            self._audit(project_id, "project_created", project_id, {})
        return self.get_project(project_id)

    def get_project(self, project_id):
        return self._project(project_id)

    def archive_project(self, project_id, *, actor):
        self._actor(actor)
        with self._transaction():
            self._project(project_id, writable=True)
            self._db.execute("UPDATE projects SET archived_at=? WHERE id=?", (utc_now(), project_id))
            self._audit(project_id, "project_archived", project_id, {"actor": actor})

    def add_prompt_version(self, project_id, label, git_commit_sha, prompt_path, content_hash):
        with self._transaction():
            self._project(project_id, writable=True)
            identity = self._insert(
                "prompt_versions", project_id=project_id, label=label, git_commit_sha=git_commit_sha,
                prompt_path=prompt_path, content_hash=content_hash, created_at=utc_now(),
            )
            self._audit(project_id, "prompt_version_added", identity, {})
        return self.get_prompt_version(project_id, identity)

    def get_prompt_version(self, project_id, version_id):
        return self._get("prompt_versions", project_id, version_id)

    def add_test_case_revision(self, project_id, case_key, input_text, expected, tags, *, actor):
        """Explicit owner-supplied reference revision; agent sources cannot call approval implicitly."""
        self._actor(actor)
        with self._transaction():
            self._project(project_id, writable=True)
            previous = self._db.execute(
                "SELECT * FROM test_cases WHERE project_id=? AND case_key=? ORDER BY revision DESC LIMIT 1",
                (project_id, case_key),
            ).fetchone()
            if previous:
                self._db.execute(
                    "UPDATE test_cases SET active=0 WHERE project_id=? AND case_key=? AND active=1",
                    (project_id, case_key),
                )
            identity = self._insert(
                "test_cases", project_id=project_id, case_key=case_key,
                revision=previous["revision"] + 1 if previous else 1, input_text=input_text,
                expected_json=encode(expected), tags_json=encode(tags),
                content_hash=digest({"input": input_text, "expected": expected, "tags": tags}),
                active=1, supersedes_id=previous["id"] if previous else None, created_at=utc_now(),
            )
            self._audit(project_id, "test_case_revised", identity, {"actor": actor})
        return self.get_test_case(project_id, identity)

    def get_test_case(self, project_id, case_id):
        return self._get("test_cases", project_id, case_id)

    def get_active_test_cases(self, project_id):
        self._project(project_id)
        return [dict(row) for row in self._db.execute(
            "SELECT * FROM test_cases WHERE project_id=? AND active=1 ORDER BY case_key", (project_id,)
        )]

    def propose_policy_revision(self, project_id, rules, *, actor, reason):
        self._actor(actor)
        if not reason.strip():
            raise InvalidStateTransition("Policy correction reason is required.")
        with self._transaction():
            self._project(project_id, writable=True)
            revision = self._db.execute(
                "SELECT COALESCE(MAX(revision),0)+1 FROM evaluation_policies WHERE project_id=?",
                (project_id,),
            ).fetchone()[0]
            previous = self._active_policy(project_id)
            identity = self._insert(
                "evaluation_policies", project_id=project_id, revision=revision,
                rules_json=encode(rules), status="pending", supersedes_id=previous["id"] if previous else None,
                created_at=utc_now(),
            )
            self._audit(project_id, "policy_proposed", identity, {"actor": actor, "reason": reason})
        return self.get_policy(project_id, identity)

    def _active_policy(self, project_id):
        row = self._db.execute(
            "SELECT * FROM evaluation_policies WHERE project_id=? AND status='approved' "
            "ORDER BY revision DESC LIMIT 1", (project_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_active_policy(self, project_id):
        self._project(project_id)
        row = self._active_policy(project_id)
        if row is None:
            raise RecordNotFound("No approved policy for this project.")
        return row

    def get_policy(self, project_id, policy_id):
        return self._get("evaluation_policies", project_id, policy_id)

    def approve_policy_revision(self, project_id, policy_id, *, actor):
        self._actor(actor)
        with self._transaction():
            self._project(project_id, writable=True)
            candidate = self.get_policy(project_id, policy_id)
            if candidate["status"] != "pending":
                raise InvalidStateTransition("Only pending policies may be approved once.")
            current = self._active_policy(project_id)
            if current and (candidate["revision"] <= current["revision"]
                            or candidate["supersedes_id"] != current["id"]):
                raise SupersededPolicy("Policy proposal is stale; propose a revision of the current policy.")
            if current:
                self._db.execute(
                    "UPDATE evaluation_policies SET status='superseded' WHERE project_id=? AND id=?",
                    (project_id, current["id"]),
                )
            self._db.execute(
                "UPDATE evaluation_policies SET status='approved',approved_at=?,approved_by=? "
                "WHERE project_id=? AND id=?", (utc_now(), actor, project_id, policy_id),
            )
            self._audit(project_id, "policy_approved", policy_id, {"actor": actor})
        return self.get_policy(project_id, policy_id)

    def create_review_cycle(self, project_id, cycle_key, prompt_version_id, policy_id=None):
        with self._transaction():
            self._project(project_id, writable=True)
            self.get_prompt_version(project_id, prompt_version_id)
            active = self.get_active_policy(project_id)
            if policy_id is not None:
                self.get_policy(project_id, policy_id)
                if policy_id != active["id"]:
                    raise SupersededPolicy("New cycles require the current approved policy.")
            identity = self._insert(
                "review_cycles", project_id=project_id, cycle_key=cycle_key,
                prompt_version_id=prompt_version_id, policy_id=active["id"], status="pending", created_at=utc_now(),
            )
            self._audit(project_id, "cycle_created", identity, {}, identity)
        return self.get_review_cycle(project_id, identity)

    def get_review_cycle(self, project_id, cycle_id):
        return self._get("review_cycles", project_id, cycle_id)

    def transition_cycle(self, project_id, cycle_id, status):
        allowed = {"pending": {"running", "needs_review"},
                   "running": {"completed", "needs_review"}, "needs_review": {"running"}, "completed": set()}
        with self._transaction():
            self._project(project_id, writable=True)
            current = self.get_review_cycle(project_id, cycle_id)
            if status not in allowed[current["status"]]:
                raise InvalidStateTransition("Invalid review status transition.")
            self._db.execute(
                "UPDATE review_cycles SET status=?,completed_at=? WHERE project_id=? AND id=?",
                (status, utc_now() if status == "completed" else None, project_id, cycle_id),
            )
            self._audit(project_id, "cycle_status_changed", cycle_id, {"status": status}, cycle_id)

    def record_planner_decision(self, project_id, cycle_id, memory_enabled, decision, model_id):
        with self._transaction():
            self._project(project_id, writable=True)
            self.get_review_cycle(project_id, cycle_id)
            identity = self._insert(
                "planner_decisions", project_id=project_id, cycle_id=cycle_id, memory_enabled=int(memory_enabled),
                decision_json=encode(decision), model_id=model_id, created_at=utc_now(),
            )
            self._audit(project_id, "planner_decision_recorded", identity, {}, cycle_id)
        return self._get("planner_decisions", project_id, identity)

    def get_planner_decision(self, project_id, decision_id):
        return self._get("planner_decisions", project_id, decision_id)

    def record_failure(self, project_id, cycle_id, fingerprint, category, evidence):
        self._safe({"fingerprint": fingerprint, "category": category, "evidence": evidence})
        with self._transaction():
            self._project(project_id, writable=True)
            self.get_review_cycle(project_id, cycle_id)
            old = self._db.execute(
                "SELECT * FROM failure_memories WHERE project_id=? AND fingerprint=?", (project_id, fingerprint)
            ).fetchone()
            if old:
                identity = old["id"]
                self._db.execute(
                    "UPDATE failure_memories SET category=?,status=?,last_cycle_id=?,evidence_json=?,updated_at=? "
                    "WHERE project_id=? AND id=?",
                    (category, "regressed" if old["status"] == "resolved" else old["status"],
                     cycle_id, encode(evidence), utc_now(), project_id, identity),
                )
            else:
                identity = self._insert(
                    "failure_memories", project_id=project_id, fingerprint=fingerprint, category=category,
                    status="open", first_cycle_id=cycle_id, last_cycle_id=cycle_id,
                    evidence_json=encode(evidence), updated_at=utc_now(),
                )
            self._audit(project_id, "failure_recorded", identity,
                        {"fingerprint": fingerprint, "category": category, "evidence": evidence}, cycle_id)
        return self.get_failure(project_id, identity)

    def get_failure(self, project_id, failure_id):
        return self._get("failure_memories", project_id, failure_id)

    def resolve_failure(self, project_id, failure_id, cycle_id, evidence):
        self._safe(evidence)
        with self._transaction():
            self._project(project_id, writable=True)
            old = self.get_failure(project_id, failure_id)
            self.get_review_cycle(project_id, cycle_id)
            if old["status"] == "resolved":
                raise InvalidStateTransition("Risk is already resolved.")
            self._db.execute(
                "UPDATE failure_memories SET status='resolved',last_cycle_id=?,evidence_json=?,updated_at=? "
                "WHERE project_id=? AND id=?", (cycle_id, encode(evidence), utc_now(), project_id, failure_id),
            )
            self._audit(project_id, "failure_resolved", failure_id, {"evidence": evidence}, cycle_id)

    def get_open_risks(self, project_id):
        self._project(project_id)
        return [dict(row) for row in self._db.execute(
            "SELECT * FROM failure_memories WHERE project_id=? AND status IN ('open','regressed') "
            "ORDER BY updated_at,id", (project_id,),
        )]

    def add_human_decision(self, project_id, prompt_version_id, cycle_id, decision, *, actor, comments=""):
        self._actor(actor)
        if decision not in {"approved", "rejected"}:
            raise InvalidStateTransition("Human decision must be approved or rejected.")
        with self._transaction():
            self._project(project_id, writable=True)
            self.get_prompt_version(project_id, prompt_version_id)
            cycle = self.get_review_cycle(project_id, cycle_id)
            if cycle["prompt_version_id"] != prompt_version_id:
                raise InvalidStateTransition("Decision version must match the review cycle.")
            if cycle["status"] != "completed":
                raise InvalidStateTransition("Human decision requires a completed review.")
            identity = self._insert(
                "human_decisions", project_id=project_id, prompt_version_id=prompt_version_id,
                cycle_id=cycle_id, decision=decision, actor=actor, comments=comments, created_at=utc_now(),
            )
            self._audit(project_id, "human_decision_recorded", identity, {"decision": decision, "actor": actor}, cycle_id)
        return self._get("human_decisions", project_id, identity)

    def get_human_decisions(self, project_id):
        self._project(project_id)
        return [dict(row) for row in self._db.execute(
            "SELECT * FROM human_decisions WHERE project_id=? ORDER BY created_at,id", (project_id,)
        )]

    def begin_tool_operation(self, project_id, cycle_id, operation_key, tool, request_hash):
        with self._transaction():
            self._project(project_id, writable=True)
            self.get_review_cycle(project_id, cycle_id)
            identity = self._insert(
                "tool_operations", project_id=project_id, cycle_id=cycle_id, operation_key=operation_key,
                tool=tool, status="pending", request_hash=request_hash, created_at=utc_now(), updated_at=utc_now(),
            )
            self._audit(project_id, "tool_operation_started", identity, {}, cycle_id)
        return self.get_tool_operation(project_id, operation_key)

    def get_tool_operation(self, project_id, operation_key):
        row = self._db.execute(
            "SELECT * FROM tool_operations WHERE project_id=? AND operation_key=?", (project_id, operation_key)
        ).fetchone()
        if row is None:
            raise RecordNotFound("Operation not found in this project.")
        return dict(row)

    def _finish_operation(self, project_id, operation, status, details, result_ref=None):
        self._safe(result_ref)
        if operation["status"] == "completed":
            raise DuplicateOperation("Operation is already completed.")
        self._db.execute(
            "UPDATE tool_operations SET status=?,result_ref=?,updated_at=? WHERE project_id=? AND id=?",
            (status, result_ref, utc_now(), project_id, operation["id"]),
        )
        self._insert("operation_attempts", project_id=project_id, operation_id=operation["id"],
                     status=status, details_json=encode(redact(details)), created_at=utc_now())
        self._audit(project_id, "tool_operation_" + status, operation["id"], details, operation["cycle_id"])

    def finish_tool_operation(self, project_id, operation_key, *, success, details, result_ref=None):
        with self._transaction():
            self._project(project_id, writable=True)
            operation = self.get_tool_operation(project_id, operation_key)
            self._finish_operation(project_id, operation, "completed" if success else "failed", details, result_ref)

    def get_operation_attempts(self, project_id, operation_key):
        operation = self.get_tool_operation(project_id, operation_key)
        return [dict(row) for row in self._db.execute(
            "SELECT * FROM operation_attempts WHERE project_id=? AND operation_id=? ORDER BY created_at,id",
            (project_id, operation["id"]),
        )]

    def record_test_execution(self, project_id, cycle_id, test_case_id, operation_key, *,
                              provider, model_id, response, validation, status, elapsed_ms):
        if status not in {"pass", "fail", "uncertain"}:
            raise InvalidStateTransition("Invalid extraction result status.")
        with self._transaction():
            self._project(project_id, writable=True)
            self.get_review_cycle(project_id, cycle_id)
            self.get_test_case(project_id, test_case_id)
            operation = self.get_tool_operation(project_id, operation_key)
            if operation["cycle_id"] != cycle_id:
                raise InvalidStateTransition("Operation belongs to a different cycle.")
            if operation["status"] == "completed":
                raise DuplicateOperation("Operation is already completed.")
            identity = self._insert(
                "test_executions", project_id=project_id, cycle_id=cycle_id, test_case_id=test_case_id,
                operation_key=operation_key, provider=provider, model_id=model_id,
                response_json=encode(response), validation_json=encode(validation), status=status,
                elapsed_ms=elapsed_ms, created_at=utc_now(),
            )
            self._finish_operation(project_id, operation, "completed", {"execution_id": identity}, identity)
            self._audit(project_id, "test_execution_recorded", identity, {}, cycle_id)
        return self.get_test_execution(project_id, identity)

    def get_test_execution(self, project_id, execution_id):
        return self._get("test_executions", project_id, execution_id)

    def append_audit_event(self, project_id, event_type, ref_id, details, cycle_id=None):
        with self._transaction():
            self._project(project_id, writable=True)
            if cycle_id is not None:
                self.get_review_cycle(project_id, cycle_id)
            identity = self._audit(project_id, event_type, ref_id, details, cycle_id)
        return self._get("audit_events", project_id, identity)

    def get_project_timeline(self, project_id):
        self._project(project_id)
        return [dict(row) for row in self._db.execute(
            "SELECT * FROM audit_events WHERE project_id=? ORDER BY created_at,rowid", (project_id,)
        )]
