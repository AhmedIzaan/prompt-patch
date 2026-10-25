"""Link existing audited read tools to the active CLI review cycle."""
from promptpatch.git_tool import GitEvidenceTool
from promptpatch.memory_tool import MemoryTools
from promptpatch.repository import Repository
from promptpatch.tool_support import ToolError


class CycleAudit:
    cycle_id: str

    def _invoke(self, project_id, tool, action):
        try:
            result = super()._invoke(project_id, tool, action)
        except ToolError as exc:
            with Repository(self.db_path) as store:
                store.append_audit_event(project_id, "review_tool_failed", self.cycle_id,
                                         {"tool": tool, "error_code": exc.code}, self.cycle_id)
            raise
        if isinstance(result, dict):
            refs = result.get("source_refs", [result["source_ref"]] if "source_ref" in result else [])
        else:
            refs = result.source_refs if hasattr(result, "source_refs") else [result.source_ref]
        event = "review_memory_read" if tool in {"retrieve_memory", "read_active_policy"} else "review_source_read"
        with Repository(self.db_path) as store:
            store.append_audit_event(project_id, event, self.cycle_id,
                                     {"tool": tool, "source_refs": refs}, self.cycle_id)
        return result


class CycleGitTools(CycleAudit, GitEvidenceTool):
    pass


class CycleMemoryTools(CycleAudit, MemoryTools):
    pass
