"""One real Module 05 Gemini smoke call, never replay or a full agent review.

Requires locally configured GEMINI_API_KEY/GEMINI_MODEL and seeded demo data.
Repeated identical calls reuse the saved operation. No prompt promotion occurs.
"""

import argparse
import sqlite3
import sys

from pydantic import ValidationError

from promptpatch.config import ConfigurationError, load_settings
from promptpatch.errors import StoreError
from promptpatch.evaluator import EvaluationConfigError
from promptpatch.executor import ExecutionError, TestExecutor
from promptpatch.git_tool import GitEvidenceTool, RepositoryAccess
from promptpatch.model_provider import GeminiProvider, ModelSettings, ProviderError
from promptpatch.repository import Repository, encode
from promptpatch.tool_support import ToolError, read_snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle-key", default="module05-live-check", help="Stable smoke-check identity; repeated identical requests reuse results.")
    args = parser.parse_args(argv)
    try:
        settings = load_settings()
        missing = [name for name, value in (("GEMINI_API_KEY", settings.gemini_api_key),
                                            ("GEMINI_MODEL", settings.gemini_model)) if not value]
        if missing or settings.mode != "live":
            # Audit only an already seeded project; do not initialize a missing DB.
            try:
                with Repository(settings.db_path) as store:
                    store.append_audit_event("demo", "provider_preflight_blocked", "module05-live-check",
                                             {"missing_variables": missing, "requires_live_mode": True})
            except (StoreError, OSError, sqlite3.Error):
                pass
            print("BLOCKED: set GEMINI_API_KEY and GEMINI_MODEL in the local process environment and use live mode. No API call or test result created.", file=sys.stderr)
            return 2
        provider = GeminiProvider(settings.gemini_api_key)
        model = ModelSettings(model_id=settings.gemini_model, max_attempts=1)
        with read_snapshot(settings.db_path) as connection:
            version = connection.execute(
                "SELECT * FROM prompt_versions WHERE project_id='demo' AND label='v3'"
            ).fetchone()
            case = connection.execute(
                "SELECT * FROM test_cases WHERE project_id='demo' AND case_key='T02' AND active=1"
            ).fetchone()
            existing = connection.execute(
                "SELECT * FROM review_cycles WHERE project_id='demo' AND cycle_key=?", (args.cycle_key,)
            ).fetchone()
        if version is None or case is None:
            raise ExecutionError("seed_demo_first")
        tool = GitEvidenceTool(settings.db_path, {"demo": RepositoryAccess(settings.demo_repo, frozenset({version["prompt_path"]}))})
        prompt = tool.read_git_prompt("demo", version["git_commit_sha"], version["prompt_path"])
        with Repository(settings.db_path) as store:
            cycle = dict(existing) if existing else store.create_review_cycle("demo", args.cycle_key, version["id"])
        result = TestExecutor(settings.db_path, provider).execute_llm_test(
            "demo", cycle["id"], case["id"], f"module05:{cycle['id']}:T02", prompt, model,
        )
        print(encode({"check": "Module 05 live smoke only; no planner or release approval", "mode": result["response"]["mode"],
                      "execution_id": result["execution_id"], "status": result["status"], "reused": result["reused"],
                      "model_version": result["response"]["model_version"], "usage": result["response"]["usage"]}))
        return 0
    except (ConfigurationError, StoreError, EvaluationConfigError, ExecutionError, ToolError,
            ProviderError, ValidationError, OSError, sqlite3.Error) as error:
        code = error.code if isinstance(error, (ExecutionError, ToolError, ProviderError)) else "configuration_or_store_error"
        print("BLOCKED: live provider check failed (" + code + "). No approval granted.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
