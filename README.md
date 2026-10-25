# Prompt Patch

PromptPatch is a planned persistent memory-driven agent for testing settlement
measurement extraction prompts across versions. This fictional domain example
is for regression testing, not engineering judgment.

**Current status: Modules 00–01 complete.** The installable package, configuration,
local diagnostics, and test harness work. Database initialization is a placeholder;
the review workflow, model calls, and persistent memory await later modules.
See [implementation status](docs/IMPLEMENTATION_STATUS.md) and
[requirement traceability](docs/REQUIREMENT_TRACEABILITY.md).

## Setup

Verified on Python **3.14.4**, SQLite **3.46.1**, and pip **25.1.1** on Linux.
The package currently declares Python 3.14 only; other versions are unverified.
Use a virtual environment. Installation requires access to the package index.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install -e '.[dev]'
python -m pytest -q
promptpatch --help
promptpatch doctor
```

`requirements-dev.txt` records all installed development dependency versions.
Direct dependencies are also pinned in `pyproject.toml`: Pydantic **2.14.1**,
pytest **9.1.1**, and setuptools **84.2.1** (build backend). CLI parsing and SQLite
use the Python standard library. Gemini and LangGraph dependencies are deferred
until their authorized integration modules.

## Configuration

The application reads the process environment. `.env.example` documents variable
names and defaults; `.env` files are **not loaded automatically**. Supply an
authorized key using your local environment or secret manager, never chat,
source, or committed files. Module 01 does not require a key or make API calls.

| Variable | Default / meaning |
|---|---|
| `GEMINI_API_KEY` | Unset; secret, excluded from configuration repr/export |
| `GEMINI_MODEL` | Unset; choose and verify a supported model in Module 05 |
| `PROMPTPATCH_DB_PATH` | `data/promptpatch.sqlite3` |
| `PROMPTPATCH_CHECKPOINT_DB_PATH` | `data/checkpoints.sqlite3` |
| `PROMPTPATCH_DEMO_REPO` | `samples/demo_git_repo` |
| `PROMPTPATCH_MODE` | `live`; allowed values: `live`, `replay` |

Blank environment values use defaults. Relative paths use the current working
directory. Reading settings creates no files. Mode selection is configuration
only at this stage; neither live inference nor replay execution is implemented.

## Current CLI contract

| Command | Behavior / exit code |
|---|---|
| `promptpatch --help` | Show commands; exit 0 |
| `promptpatch --version` | Show package version; exit 0 |
| `promptpatch doctor` | Local runtime/configuration summary, no writes/network; exit 0 means inspection completed, not provider/workflow readiness |
| `promptpatch init` | Explicit “Not implemented” for Module 02; exit 1 and no files created |

Invalid configuration or command syntax exits 2. Doctor displays whether the key
and model are set without displaying their contents. Provider remains **not
connected** until a real integration is tested. Teacher approval remains
**pending/unverified**.

Eight tests verify package installation, defaults/environment overrides, secret
handling, help/doctor output, invalid configuration, and the init placeholder's
lack of writes. No database or model behavior is claimed tested.

Codex assisted with inspection, documentation, and the Module 01 implementation.
The student must review, understand, and be able to modify submitted code.
No external datasets have been imported. Third-party dependencies are listed
above. Development proceeds one explicitly authorized module at a time; next is
Module 02, after approval.
