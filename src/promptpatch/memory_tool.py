"""Bounded, project-scoped retrieval of persisted decisions and evidence."""

import json

from promptpatch.repository import encode
from promptpatch.tool_support import AuditedTools, ToolError, read_snapshot


def _decode_row(row):
    result = dict(row)
    for key in list(result):
        if key.endswith("_json"):
            value = result.pop(key)
            result[key[:-5]] = json.loads(value) if value is not None else None
    return result


class MemoryTools(AuditedTools):
    def __init__(self, db_path, *, max_memory_bytes=131072):
        super().__init__(db_path)
        if max_memory_bytes < 1:
            raise ValueError("Memory output budget must be positive.")
        self.max_memory_bytes = max_memory_bytes

    @staticmethod
    def _filters(tags, open_only, limit):
        if type(limit) is not int or not 1 <= limit <= 50 or type(open_only) is not bool:
            raise ToolError("invalid_filter", "Limit must be 1–50 and open_only must be boolean.")
        if tags is None:
            return []
        if not isinstance(tags, (list, tuple)) or len(tags) > 10:
            raise ToolError("invalid_filter", "Tags must be a bounded list of strings.")
        if any(not isinstance(tag, str) or not 1 <= len(tag) <= 64 for tag in tags):
            raise ToolError("invalid_filter", "Each tag must contain 1–64 characters.")
        return sorted(set(tags))

    def _bounded(self, result):
        if len(encode(result).encode("utf-8")) > self.max_memory_bytes:
            raise ToolError("memory_limit", "Memory evidence exceeds the output budget; request fewer records.")
        return result

    def read_active_policy(self, project_id):
        def read():
            with read_snapshot(self.db_path) as connection:
                row = connection.execute(
                    "SELECT * FROM evaluation_policies WHERE project_id=? AND status='approved' "
                    "ORDER BY revision DESC LIMIT 1", (project_id,),
                ).fetchone()
            if row is None:
                raise ToolError("no_approved_policy", "No approved current policy is available.")
            result = _decode_row(row)
            result["source_ref"] = f"policy:{row['id']}"
            return self._bounded(result), [result["source_ref"]]
        return self._invoke(project_id, "read_active_policy", read)

    def retrieve_memory(self, project_id, tags=None, open_only=True, limit=10):
        """Limit each collection; tags filter risk categories and tagged case evidence.

        Human decisions and policy corrections remain project-wide because their
        approval constraints apply across test categories. No pending policy is
        presented as an approved correction. Source bodies/raw responses are omitted.
        """
        def read():
            selected_tags = self._filters(tags, open_only, limit)
            result = {"project_id": project_id, "per_collection_limit": limit, "truncated": {}}

            def collect(connection, name, sql, params):
                rows = connection.execute(sql + " LIMIT ?", (*params, limit + 1)).fetchall()
                result[name] = [_decode_row(row) for row in rows[:limit]]
                result["truncated"][name] = len(rows) > limit

            risk_filter, risk_params = "project_id=?", [project_id]
            tag_filter, tag_params = "", []
            if open_only:
                risk_filter += " AND status IN ('open','regressed')"
            if selected_tags:
                slots = ",".join("?" for _ in selected_tags)
                risk_filter += f" AND category IN ({slots})"
                risk_params.extend(selected_tags)
                tag_filter = f" AND EXISTS(SELECT 1 FROM json_each(t.tags_json) jt WHERE jt.value IN ({slots}))"
                tag_params = selected_tags
            with read_snapshot(self.db_path) as connection:
                collect(connection, "risks", "SELECT * FROM failure_memories WHERE " + risk_filter
                        + " ORDER BY updated_at DESC,id DESC", risk_params)
                risk_ids = [row["id"] for row in result["risks"]]
                if risk_ids:
                    slots = ",".join("?" for _ in risk_ids)
                    collect(connection, "failure_history",
                            "SELECT * FROM audit_events WHERE project_id=? "
                            f"AND ref_id IN ({slots}) AND event_type IN ('failure_recorded','failure_resolved') "
                            "ORDER BY created_at DESC,id DESC", [project_id, *risk_ids])
                else:
                    result["failure_history"] = []
                    result["truncated"]["failure_history"] = False
                collect(connection, "outcomes",
                        "SELECT e.id,e.project_id,e.cycle_id,e.test_case_id,e.operation_key,e.status,"
                        "e.validation_json,e.created_at,t.case_key,t.tags_json FROM test_executions e "
                        "JOIN test_cases t ON t.project_id=e.project_id AND t.id=e.test_case_id "
                        "WHERE e.project_id=?" + tag_filter + " ORDER BY e.created_at DESC,e.id DESC",
                        [project_id, *tag_params])
                collect(connection, "human_decisions",
                        "SELECT * FROM human_decisions WHERE project_id=? ORDER BY created_at DESC,id DESC",
                        [project_id])
                collect(connection, "policy_corrections",
                        "SELECT p.*, (SELECT a.details_json FROM audit_events a WHERE a.project_id=p.project_id "
                        "AND a.ref_id=p.id AND a.event_type='policy_proposed' ORDER BY a.created_at DESC,a.id DESC LIMIT 1) "
                        "AS proposal_json FROM evaluation_policies p WHERE p.project_id=? AND p.revision>1 "
                        "AND p.status IN ('approved','superseded') ORDER BY p.revision DESC", [project_id])
                collect(connection, "case_corrections",
                        "SELECT t.id,t.project_id,t.case_key,t.revision,t.active,t.supersedes_id,t.created_at,t.tags_json,"
                        "(SELECT a.details_json FROM audit_events a WHERE a.project_id=t.project_id AND a.ref_id=t.id "
                        "AND a.event_type='test_case_revised' ORDER BY a.created_at DESC,a.id DESC LIMIT 1) AS attribution_json "
                        "FROM test_cases t WHERE t.project_id=? AND t.revision>1" + tag_filter
                        + " ORDER BY t.created_at DESC,t.id DESC", [project_id, *tag_params])
            prefixes = {"risks": "risk", "failure_history": "audit", "outcomes": "execution",
                        "human_decisions": "human_decision", "policy_corrections": "policy", "case_corrections": "case"}
            refs = [f"{prefix}:{row['id']}" for name, prefix in prefixes.items() for row in result[name]]
            result["source_refs"] = refs
            return self._bounded(result), refs
        return self._invoke(project_id, "retrieve_memory", read)
