"""Shared audit boundaries and read-only snapshots for evidence tools."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from time import perf_counter
from uuid import uuid4

from promptpatch.errors import RecordNotFound, StoreError
from promptpatch.repository import Repository


class ToolError(RuntimeError):
    """Safe tool failure; code/message never include untrusted input or stderr."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@contextmanager
def read_snapshot(path: Path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN")
        yield connection
    finally:
        connection.close()


class AuditedTools:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def _invoke(self, project_id, tool, action):
        call_id = str(uuid4())
        started = perf_counter()
        try:
            with Repository(self.db_path) as store:
                try:
                    project = store.get_project(project_id)
                except RecordNotFound:
                    raise ToolError("project_unavailable", "Project is unavailable.") from None
                # Archived projects forbid audit writes, so fail without changing them.
                if project["archived_at"] is not None:
                    raise ToolError("project_unavailable", "Project is unavailable.")
                store.append_audit_event(project_id, "tool_invoked", call_id, {"tool": tool})
                try:
                    result, evidence_refs = action()
                except ToolError as error:
                    store.append_audit_event(project_id, "tool_failed", call_id, {
                        "tool": tool, "error_code": error.code,
                        "elapsed_ms": round((perf_counter() - started) * 1000, 3),
                    })
                    raise
                except (OSError, sqlite3.Error, StoreError, ValueError, TypeError):
                    store.append_audit_event(project_id, "tool_failed", call_id, {
                        "tool": tool, "error_code": "evidence_unavailable",
                        "elapsed_ms": round((perf_counter() - started) * 1000, 3),
                    })
                    raise ToolError("evidence_unavailable", "Evidence could not be read safely.") from None
                if tool in {"retrieve_memory", "read_active_policy"}:
                    store.append_audit_event(project_id, "memory_read", call_id, {
                        "tool": tool, "evidence_refs": evidence_refs,
                    })
                store.append_audit_event(project_id, "tool_succeeded", call_id, {
                    "tool": tool, "evidence_refs": evidence_refs,
                    "elapsed_ms": round((perf_counter() - started) * 1000, 3),
                })
                return result
        except ToolError:
            raise
        except (OSError, sqlite3.Error, StoreError):
            # No evidence is returned as successful if auditing/storage fails.
            raise ToolError("audit_unavailable", "Tool audit storage is unavailable.") from None
