"""Module 01 CLI foundation. No provider calls or persistent writes yet."""

import argparse
import sqlite3
import sys

from promptpatch import __version__
from promptpatch.config import ConfigurationError, load_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="promptpatch", description="PromptPatch prompt regression testing (Module 01 foundation)."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspect local readiness; no network calls or writes.")
    commands.add_parser("init", help="Database initialization placeholder (Module 02).")
    args = parser.parse_args(argv)

    if args.command == "init":
        print("Not implemented: database initialization is planned for Module 02.", file=sys.stderr)
        return 1

    try:
        settings = load_settings()
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"PromptPatch {__version__} — Module 01 foundation")
    print(f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"SQLite: {sqlite3.sqlite_version}")
    print(f"Mode: {settings.mode}")
    print("GEMINI_API_KEY: " + ("set (not validated)" if settings.gemini_api_key else "not set"))
    print("GEMINI_MODEL: " + ("set (not validated)" if settings.gemini_model else "not set"))
    print("Provider: not connected (integration planned for Module 05)")
    print("Database initialization: not implemented (Module 02)")
    print("Doctor completed local inspection only; review workflow is not ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
