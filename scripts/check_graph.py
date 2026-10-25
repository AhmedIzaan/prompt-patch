"""Module 06 single-graph integration check, separate from the future review CLI.

Requires already seeded data and locally configured Gemini environment variables.
No seed, corrections, approvals, release, or full three-cycle demonstration.
"""
import argparse
import json
from pathlib import Path
import sys

from promptpatch.config import load_settings
from promptpatch.git_tool import GitEvidenceTool, RepositoryAccess
from promptpatch.graph import ReviewGraph
from promptpatch.model_provider import GeminiProvider, ModelSettings
from promptpatch.repository import Repository, encode
from promptpatch.tool_support import read_snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, choices=["v1", "v2", "v3"])
    parser.add_argument("--base-version", choices=["v1", "v2", "v3"])
    parser.add_argument("--cycle-key", required=True)
    parser.add_argument("--memory-off", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    settings = load_settings()
    if not settings.gemini_api_key or not settings.gemini_model or settings.mode != "live":
        print("BLOCKED: configure Gemini in the local process environment and use live mode.", file=sys.stderr)
        return 2
    with read_snapshot(settings.db_path) as db:
        versions = {row["label"]: dict(row) for row in db.execute("SELECT * FROM prompt_versions WHERE project_id='demo'")}
        row = db.execute("SELECT * FROM review_cycles WHERE project_id='demo' AND cycle_key=?", (args.cycle_key,)).fetchone()
    with Repository(settings.db_path) as store:
        cycle = dict(row) if row else store.create_review_cycle("demo", args.cycle_key, versions[args.version]["id"])
    if cycle["prompt_version_id"] != versions[args.version]["id"]:
        raise ValueError("cycle_version_mismatch")
    git = GitEvidenceTool(settings.db_path, {"demo": RepositoryAccess(settings.demo_repo, frozenset({versions[args.version]["prompt_path"]}))})
    runner = ReviewGraph(settings.db_path, settings.checkpoint_db_path, git, GeminiProvider(settings.gemini_api_key),
                         ModelSettings(model_id=settings.gemini_model, max_attempts=1))
    state = runner.run("demo", cycle["id"], memory_enabled=not args.memory_off,
                       base_version_id=versions[args.base_version]["id"] if args.base_version else None)
    with Repository(settings.db_path) as store:
        planner = store.get_planner_decision("demo", state["planner_decision_id"]) if state.get("planner_decision_id") else None
    evidence = {"module": "06", "live": True, "cycle_id": cycle["id"], "version": args.version,
                "state": state, "planner": json.loads(planner["decision_json"]) if planner else None}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encode(evidence) + "\n")
    print(encode({"cycle_id": cycle["id"], "selected_test_ids": state["selected_test_ids"],
                  "executed_test_ids": [r["test_id"] for r in state["execution_results"]],
                  "recommendation": state.get("recommendation"), "error": state.get("error"),
                  "pending_approval": state["pending_approval"]}))
    return 0 if not state.get("error") and state["execution_results"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
