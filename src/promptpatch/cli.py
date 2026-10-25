"""CLI foundation and domain database initialization; no provider calls yet."""

import argparse
import sqlite3
import sys

from promptpatch import __version__
from promptpatch.config import ConfigurationError, load_settings
from promptpatch.db import initialize_database
from promptpatch.errors import StoreError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="promptpatch", description="PromptPatch prompt regression testing (Module 02 domain memory)."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspect local readiness; no network calls or writes.")
    commands.add_parser("init", help="Initialize the persistent domain database (idempotent).")
    args = parser.parse_args(argv)

    try:
        settings = load_settings()
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.command == "init":
        try:
            if settings.db_path.resolve() == settings.checkpoint_db_path.resolve():
                raise StoreError("Domain and checkpoint databases must be separate.")
            initialize_database(settings.db_path)
        except (OSError, sqlite3.Error, StoreError):
            print("Database initialization failed. Check local paths, permissions, and schema version.", file=sys.stderr)
            return 1
        print("Domain database initialized (schema 1); existing records preserved.")
        return 0

    print(f"PromptPatch {__version__} — Module 02 domain memory")
    print(f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"SQLite: {sqlite3.sqlite_version}")
    print(f"Mode: {settings.mode}")
    print("GEMINI_API_KEY: " + ("set (not validated)" if settings.gemini_api_key else "not set"))
    print("GEMINI_MODEL: " + ("set (not validated)" if settings.gemini_model else "not set"))
    print("Provider: not connected (integration planned for Module 05)")
    print("Database initialization: available via promptpatch init (not checked by doctor)")
    print("Doctor completed local inspection only; review workflow is not ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
