# Prompt Patch

PromptPatch is a planned persistent memory-driven agent for testing settlement
measurement extraction prompts across versions. This fictional domain example
is for regression testing, not engineering judgment.

**Current status: Modules 00–02 complete.** The installable package, configuration,
local diagnostics, persistent SQLite domain store, and test harness work.
The review workflow, model calls, and agent/checkpoint integration await later modules.
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
source, or committed files. Modules 01–02 do not require a key or make API calls.

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
| `promptpatch init` | Create parent directory and initialize schema 1 at `PROMPTPATCH_DB_PATH`; preserve existing records on repeat; exit 0 on success, 1 on initialization failure |

Invalid configuration or command syntax exits 2. Doctor displays whether the key
and model are set without displaying their contents. Provider remains **not
connected** until a real integration is tested. Teacher approval remains
**pending/unverified**.

## Domain memory (Module 02)

```bash
promptpatch init
```

Only the domain database is initialized. The checkpoint database remains separate
and awaits Module 06. Doctor performs no database reads or writes. Domain and
checkpoint paths must differ. Schema migrations use SQLite `user_version`; schema
1 creation is transactional and repeatable, including concurrent initialization.
A newer schema is rejected without changing it.

`promptpatch.repository.Repository(Path(...))` opens an already initialized store
and supports project creation/archiving, immutable prompt versions, reference-case
revisions, policy proposals/approvals, review cycles, risks, planner decisions,
human decisions, tool operations/attempts, results, and audit events. This is a
storage API; review/approval CLI commands await Module 07.

All record lookups require a project ID. Scoped foreign keys also prevent records
from mixing projects. UUIDs identify records; caller-supplied project IDs, cycle
keys, and operation keys provide stable identities. Writes and their audit events
commit together under `BEGIN IMMEDIATE`, with foreign keys enabled on every store
connection. UTC timestamps and canonical JSON/hashes preserve provenance.

Policy proposals stay pending. A separate `approve_policy_revision` call with an
explicit actor activates a policy and supersedes the old one. Stale proposals
must be reproposed against the current policy. Old rules remain queryable, and
existing cycles retain their original policy. New cycles use the approved current
policy. Test-case revisions require an explicit actor, deactivate the old revision,
and retain its content and hash. Callers are trusted local developer code; an actor
string records attribution, and is not an authentication mechanism.

Prompt/source content, results, planner decisions, human decisions, attempts, and
audit history have SQLite mutation guards. Risk rows are current-state summaries;
their earlier evidence survives in append-only audit events. Resolved risks reopen
as regressed when contrary evidence arrives. One human decision per completed
cycle and one completed result per operation key prevent duplicate approvals and
results. Failure attempts remain separate from the completed logical operation.
Store code records outcomes supplied by callers; it does not validate model outputs
or grant release approval automatically.

The owner can archive a project with an explicit actor; reads remain available
and further writes are blocked. No deletion API or automatic expiry is provided;
source/evaluation/decision history is retained. Database files are local,
gitignored, and authoritative for domain records. Full privacy/retention tooling,
log redaction hardening, and safe exports await later authorized modules.

Tests cover fresh connections and a fresh Python process, corrections, isolation,
foreign keys, retries/deduplication, atomic writes/audits, immutable history,
concurrent initialization, and CLI behavior. All stored test outputs are explicitly
synthetic offline fixtures; no model integration is claimed tested.

Codex assisted with inspection, documentation, and the Modules 01–02 implementation.
The student must review, understand, and be able to modify submitted code.
No external datasets have been imported. Third-party dependencies are listed
above. Development proceeds one explicitly authorized module at a time; next is
Module 03, after approval.
