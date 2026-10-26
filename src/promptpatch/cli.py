"""Local developer workflow: explicit reviews, corrections and approval records."""
import argparse
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from promptpatch import __version__
from promptpatch.config import ConfigurationError, load_settings
from promptpatch.db import initialize_database
from promptpatch.errors import StoreError
from promptpatch.repository import Repository
from promptpatch.model_provider import ProviderError
from promptpatch.tool_support import ToolError


def _parser():
    parser = argparse.ArgumentParser(prog="promptpatch", description="Persistent prompt regression reviews and explicit developer approvals.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspect local configuration; no network or writes.")
    commands.add_parser("init", help="Initialize the domain database (idempotent).")
    demo = commands.add_parser("demo").add_subparsers(dest="action", required=True)
    seed = demo.add_parser("seed", help="Create the fictional baseline using the existing fixture script.")
    seed.add_argument("--actor", required=True)
    seed.add_argument("--approve-baseline", action="store_true", required=True)
    review = commands.add_parser("review").add_subparsers(dest="action", required=True)
    for action in ("start", "status", "resume"):
        item = review.add_parser(action)
        item.add_argument("--project", required=True)
        item.add_argument("--cycle", required=True, help="Stable project-scoped cycle key.")
        if action == "start":
            item.add_argument("--version", required=True)
            item.add_argument("--base-version")
            item.add_argument("--timeout-ms", type=int, default=20000, help="Bounded model request timeout: 1000–30000 ms; saved for resume.")
            item.add_argument("--memory-off", action="store_true")
            item.add_argument("--replay-file", type=Path)
            item.add_argument("--replay-scenario")
    memory = commands.add_parser("memory").add_subparsers(dest="action", required=True)
    memory.add_parser("show").add_argument("--project", required=True)
    policy = commands.add_parser("policy").add_subparsers(dest="action", required=True)
    proposal = policy.add_parser("propose")
    proposal.add_argument("--project", required=True)
    proposal.add_argument("--file", type=Path, required=True)
    proposal.add_argument("--actor", required=True)
    proposal.add_argument("--reason", required=True)
    approval = policy.add_parser("approve")
    approval.add_argument("--project", required=True)
    approval.add_argument("--revision", type=int, required=True)
    approval.add_argument("--actor", required=True)
    version = commands.add_parser("version").add_subparsers(dest="action", required=True)
    for action in ("approve", "reject"):
        item = version.add_parser(action)
        item.add_argument("--project", required=True)
        item.add_argument("--version", required=True)
        item.add_argument("--cycle", required=True, help="Exact completed review whose recommendation you inspected.")
        item.add_argument("--actor", required=True)
        item.add_argument("--comments", default="")
    logs = commands.add_parser("logs").add_subparsers(dest="action", required=True)
    show = logs.add_parser("show")
    show.add_argument("--project", required=True)
    show.add_argument("--cycle", help="Optional cycle key; omit for project-wide policy/approval events too.")
    return parser


def _dispatch(args, settings):
    from promptpatch.approvals import propose_policy, approve_policy, decide_version
    from promptpatch.memory_tool import MemoryTools
    from promptpatch.reviews import Reviews, cycle_by_key, ReviewError

    if args.command == "demo":
        script = Path(__file__).resolve().parents[2] / "scripts/seed_demo.py"
        if not script.is_file():
            raise ReviewError("Demo seeder is unavailable; use the documented editable repository installation.")
        result = subprocess.run([sys.executable, str(script), "--db", str(settings.db_path.resolve()),
                                 "--repo", str(settings.demo_repo.resolve()), "--actor", args.actor, "--approve-baseline"],
                                capture_output=True, text=True, timeout=60, check=False)
        if result.returncode:
            raise ReviewError("Demo setup failed; check destination ownership and existing baseline consistency.")
        return json.loads(result.stdout)
    if args.command == "review":
        controller = Reviews(settings)
        if args.action == "start":
            return controller.start(args.project, args.version, args.cycle, base_label=args.base_version,
                                    memory_enabled=not args.memory_off, replay_file=args.replay_file, replay_scenario=args.replay_scenario, timeout_ms=args.timeout_ms)
        return getattr(controller, args.action)(args.project, args.cycle)
    if args.command == "memory":
        return {"active_policy": MemoryTools(settings.db_path).read_active_policy(args.project),
                "history": MemoryTools(settings.db_path).retrieve_memory(args.project)}
    if args.command == "policy":
        if args.action == "propose":
            return propose_policy(settings.db_path, args.project, args.file, actor=args.actor, reason=args.reason)
        return approve_policy(settings.db_path, args.project, args.revision, actor=args.actor)
    if args.command == "version":
        return decide_version(settings.db_path, args.project, args.version, args.cycle,
                              "approved" if args.action == "approve" else "rejected", actor=args.actor, comments=args.comments)
    with Repository(settings.db_path) as store:
        cycle = cycle_by_key(settings.db_path, args.project, args.cycle) if args.cycle else None
        events = store.get_project_timeline(args.project)
    if cycle:
        events = [r for r in events if r["cycle_id"] == cycle["id"]]
    return {"project_id": args.project, "cycle": args.cycle, "events": [
        {**{k: v for k, v in r.items() if k != "details_json"}, "details": json.loads(r["details_json"])} for r in events]}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.command == "doctor":
        print(f"PromptPatch {__version__} — local configuration")
        print(f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        print(f"SQLite: {sqlite3.sqlite_version}")
        print(f"Mode: {settings.mode}")
        print("GEMINI_API_KEY: " + ("set (not validated)" if settings.gemini_api_key else "not set"))
        print("GEMINI_MODEL: " + ("set (not validated)" if settings.gemini_model else "not set"))
        print("Provider: not connected by doctor; live integration is available through review start.")
        print("Doctor completed local inspection only; database and provider access are not verified.")
        return 0
    try:
        if settings.db_path.resolve() == settings.checkpoint_db_path.resolve():
            raise StoreError("Domain and checkpoint databases must be separate.")
        if hasattr(args, "actor") and (not args.actor.strip() or len(args.actor) > 128):
            raise ValueError("invalid_actor")
        if args.command == "init":
            initialize_database(settings.db_path)
            print("Domain database initialized (schema 1); existing records preserved.")
            return 0
        result = _dispatch(args, settings)
        rendered = json.dumps(result, indent=2, allow_nan=False)
        if settings.gemini_api_key:
            rendered = rendered.replace(settings.gemini_api_key.get_secret_value(), "[redacted]")
        print(rendered)
        if args.command == "review" and args.action != "status" and result["status"] == "needs_review":
            return 1
        return 0
    except (StoreError, ToolError, ProviderError, ValueError, OSError, sqlite3.Error, subprocess.SubprocessError) as exc:
        from promptpatch.reviews import ReviewError
        message = str(exc) if isinstance(exc, (StoreError, ToolError, ReviewError)) else "Invalid input or local configuration; check paths, policy JSON, model settings and actor."
        if isinstance(exc, ProviderError):
            message = "Provider configuration or replay failed (" + exc.code + "). No approval granted."
        if args.command == "init":
            message = "Database initialization failed. Check local paths, permissions, and schema version."
        if hasattr(args, "project"):
            try:
                with Repository(settings.db_path) as store:
                    store.append_audit_event(args.project, "cli_command_failed", "cli", {"command": args.command,
                                             "action": args.action, "error_code": type(exc).__name__})
            except (StoreError, OSError, sqlite3.Error):
                pass
        print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
