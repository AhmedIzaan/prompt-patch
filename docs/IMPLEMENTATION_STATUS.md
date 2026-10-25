# PromptPatch implementation status

Last updated: 2026-10-25 (Asia/Karachi).
Authorized scope: **Modules 00–05**. Modules 06–11 require separate explicit authorization.
The user authorized local commits from Module 01 onward; the user will push.

## Execution contract

- Read the entire master plan before work; implement one authorized module per turn.
- Inspect → explain intent → edit → run required checks → inspect results → record evidence → stop.
- Preserve existing work; no commits, pushes, submission, or unrelated changes without explicit approval.
- Record actual results only. Distinguish implemented, tested, pending, and blocked work.
- Stop after each module. Current stop: **Module 05 BLOCKED**; resolve live verification before `START MODULE 06`.

## Module checklist

Allowed statuses: `PENDING`, `IN_PROGRESS`, `DONE`, `BLOCKED`. A `DONE` entry requires recorded verification, not just implementation.

| Module | Scope | Status | Date | Tests / evidence | Notes / remaining work |
|---|---|---|---|---|---|
| 00 | Inspection, requirements, execution contract | DONE | 2026-10-25 | Workspace/runtime inspection and document read-back; see verification below and REQUIREMENT_TRACEABILITY.md | Documentation implemented and checked; application not started |
| 01 | Python foundation, config, CLI, test harness | DONE | 2026-10-25 | Editable install, 8 pytest tests, help/doctor, pip check; see Module 01 evidence below | No DB tables, provider adapter, or graph implemented |
| 02 | SQLite domain memory, versioned corrections | DONE | 2026-10-25 | 32 passing tests; CLI init twice; SQLite integrity/FK checks; fresh-process retrieval | Domain persistence implemented; checkpoints and live integrations pending |
| 03 | Curated cases and versioned local Git fixture | DONE | 2026-10-25 | 62 passing tests; actual seed twice; three real Git SHAs; SQLite counts/integrity checked | Fictional baseline only; candidate v2 remains a file; no model results |
| 04 | Read-only Git and memory tools | DONE | 2026-10-25 | 101 passing tests; actual v1/v2/v3 reads/diff, bounded memory and approved-policy lookup, audit read-back | No provider calls, evaluator, graph or workflow CLI implemented |
| 05 | Provider adapter, executor, deterministic validator | BLOCKED | 2026-10-25 | 158 tests passed; offline SDK transport/replay verified; live check exits 2 | Implemented/offline-tested; GEMINI_API_KEY and GEMINI_MODEL unset; no real API result |
| 06 | LLM planner and persistent LangGraph workflow | PENDING | — | Not run | No agent decisions or checkpoints verified |
| 07 | Workflow CLI, approvals, corrections | PENDING | — | Not run | No approval functionality implemented |
| 08 | Three cycles and full process restart | PENDING | — | Not run | Live/replay outputs and restart evidence absent |
| 09 | Reliability, security, isolation, retries | PENDING | — | Not run | Negative cases and telemetry pending |
| 10 | Ten scenarios, three memory comparisons, measurements | PENDING | — | Not run | No evaluation results claimed |
| 11 | Reproducibility, report, submission and demo docs | PENDING | — | Not run | Report/demo/package pending; no publishing authorized |

## Module 00 findings

- Working directory: `/mnt/data2/Documents/6thSem/agentic/ass2/promptpatch`.
- Initial file inventory: `PROMPTPATCH_CODEX_MASTER_PLAN.md` (749 lines); `.git`, `.agents`, `.codex`, and `.aws` were empty protected directories. No existing PromptPatch code, README, package configuration, tests, or status document found.
- No `AGENTS.md` found at the workspace root or inspected ancestor paths. Protected instruction directories contained no files.
- Assignment PDF: **absent from this workspace** (`find . -type f -iname '*.pdf' -print` returned no paths). Requirements are mapped from the master plan's complete checklist; the PDF itself has not been verified.
- Git: executable available, version **2.53.0**. The directory is **not a valid Git repository** despite an empty `.git` directory. Branch and tracked/untracked status unavailable. No repository initialized or altered.
- Runtime: `/usr/bin/python3`, **Python 3.14.4**; pip **25.1.1**; SQLite **3.46.1**; pytest **9.0.2**.
- Package metadata in this interpreter: `pydantic`, `typer`, `google-genai`, `langgraph`, and `langgraph-checkpoint-sqlite` **not installed**. Compatibility and dependency pins are not yet verified; no packages installed in Module 00.
- `GEMINI_API_KEY`: **not set** in the inspected environment. Only presence was checked; no secret values displayed.
- Provider: **not connected**. No API requests, authentication/quota checks, model selection, or integration successes claimed.
- Teacher approval: **pending/unverified**. No actual teacher decision supplied; none assumed.

## Prerequisites and layout decisions

- The user must supply an authorized `GEMINI_API_KEY` via the **local environment only**, never chat, source, or documentation. Provider connectivity must be verified in Module 05.
- Module 01 must verify dependency compatibility with the available interpreter and choose/pin actual tested versions. Use an isolated environment; do not assume installation success.
- Current workspace permissions allow documentation/source writes here and temporary files in `/tmp`; protected `.git`, `.agents`, `.codex`, and `.aws` are not writable. Future operational Git tools must remain read-only against evaluated repositories. Any Module 03 fixture must use its own permitted local directory, not this protected `.git`.
- No deviation from the suggested layout is proposed. Only `docs/` and the two Module 00 documents are created now. Package, CLI, database, samples, scripts, and artifacts await their modules.
- Teacher approval and provider credentials are pending external prerequisites, **not blockers for Module 00**. Git status unavailability is an environment finding, not a failed application test.

## Verification and evidence (actual execution)

| Command / check | Actual result |
|---|---|
| `pwd` and `ls -la` | Confirmed workspace path and initial inventory above |
| `wc -l PROMPTPATCH_CODEX_MASTER_PLAN.md` and `sed -n` ranges `1,220`, `221,440`, `441,660`, `661,749` | All 749 lines read without relying on truncated output |
| `rg --files` / hidden-file inventory and ancestor `AGENTS.md` inspection | Only master plan initially; no applicable additional instructions found |
| `find . -type f -iname '*.pdf' -print` | No workspace PDF found; used plan checklist as authorized |
| `git rev-parse --show-toplevel` | Exit 128: not a Git repository; chained branch/status probes did not run |
| `git status --short` (separate check) | Exit 128: not a Git repository; status unavailable, not a passing Git check |
| `python3 --version`, `python3 -m pip --version`, `git --version` | Available; versions recorded above |
| Python standard-library metadata / SQLite / environment-presence probe | Runtime and package findings above; no credentials printed |
| `sha256sum PROMPTPATCH_CODEX_MASTER_PLAN.md` before/after documentation | Master plan preserved; digest recorded below |
| `cat docs/IMPLEMENTATION_STATUS.md docs/REQUIREMENT_TRACEABILITY.md` | Read back both generated documents |
| Inline Python documentation acceptance checks | Verified module rows 00–11, 14 unique requirement rows, both documents present, master plan digest unchanged, and documentation-only file inventory |

Master plan SHA-256: `ba9243312bc06b48c42888000e863c7acace520ffffa8e51f03947a7a214af63`.

**Implemented:** Module 00 inspection report, module checklist, execution contract, and requirement mapping.
**Tested:** Documentation presence, coverage, read-back, and preservation checks only. No application tests exist or were run.
**Pending:** All application behavior, persistence, provider access, evaluations, and later deliverables.
**Blocked:** Nothing within Module 00. Future prerequisites and Git limitation are explicitly recorded above.

AI assistance disclosure: Codex performed this inspection and drafted these documents. Student review and understanding remain required; no external code or datasets were imported.

Next step after explicit approval: **Module 01 — minimal Python foundation, configuration, CLI, and testing harness**. Do not implement database tables, agent logic, or later modules.

MODULE 00 COMPLETE — STOPPED. Awaiting: START MODULE 01

## Module 01 — Python foundation, configuration, CLI and tests

Status: **DONE**. Authorized by the user's “Lets start with module 1” instruction.
Module 00 findings above are historical; current Git/runtime evidence follows.

### Current inspection and decisions

- Git is now valid on branch `main`; starting commit `842b33a` (`first commit`) tracked only the one-line README. The master plan and Module 00 docs were untracked. These related planning documents are included with the foundation commit for reproducibility. No push is performed.
- No additional `AGENTS.md` found. Existing README title and master plan preserved.
- Available Python remains 3.14.4. Package support is deliberately restricted to verified Python 3.14; other interpreters remain unverified.
- Use `argparse` and standard-library SQLite to keep the foundation small. Pydantic handles settings; `SecretStr`, excluded secret fields, and generic configuration errors prevent credential values appearing in repr, JSON export, or CLI output.
- Use a project `.venv`. Direct versions and build backend are pinned; `requirements-dev.txt` captures actual installed transitive development versions without a machine-specific editable source URL.
- Gemini/LangGraph installation is deferred to their integration modules. No model ID is guessed; `GEMINI_MODEL` defaults to unset.
- CLI contract is documented in README. Doctor reports local inspection only, never successful connectivity. Init returns exit 1 with an honest Module 02 placeholder and makes no files. Invalid settings return exit 2 without echoing environment values.
- Settings read the process environment only; no implicit .env loading. Configured paths are relative to the caller's working directory and are not created in this module.

### Files changed

`pyproject.toml`, `requirements-dev.txt`, `.gitignore`, `.env.example`,
`src/promptpatch/__init__.py`, `src/promptpatch/config.py`, `src/promptpatch/cli.py`,
`tests/test_foundation.py`, `README.md`, and this status document.
The unchanged master plan and Module 00 traceability document are also added to Git.

### Commands and actual evidence

| Command | Result |
|---|---|
| `git status --short`, `git branch --show-current`, `git log -1 --oneline`, `git ls-files` | Valid repository, `main`, initial commit and inventory above |
| `python3 -m venv .venv` | PASS: isolated environment created |
| `.venv/bin/python -m pip install pydantic pytest setuptools` (sandbox) | Failed: package-index DNS unavailable; no installation success claimed from this attempt |
| `.venv/bin/python -m pip install --no-cache-dir pydantic pytest setuptools` (network-enabled retry) | PASS: Pydantic 2.14.1, pytest 9.1.1, setuptools 84.2.1 and dependencies installed |
| `.venv/bin/python -m pip install --no-build-isolation -e '.[dev]'` | PASS: editable promptpatch 0.1.0 installed using installed build backend |
| `.venv/bin/python -m pip install --no-cache-dir -e '.[dev]'` (network-enabled) | PASS: normal isolated setuptools build and editable installation |
| `.venv/bin/python -m pytest -q` | PASS: **8 passed** in 1.24 seconds |
| `.venv/bin/promptpatch --help` | PASS: doctor/init help displayed |
| `.venv/bin/promptpatch doctor` | PASS: runtime summary, key/model unset, provider not connected, database not implemented |
| `.venv/bin/python -m pip check` | PASS: no broken requirements |
| `.venv/bin/python -m pip freeze` | Installed versions captured in requirements-dev.txt; editable source URL omitted |
| `.venv/bin/python -m pip install --no-index -r requirements-dev.txt` | PASS: all recorded pins match the installed environment |
| `.venv/bin/promptpatch --version` | PASS: promptpatch 0.1.0 |
| `git diff --check`, `git check-ignore` with representative secret/runtime/cache paths, master plan SHA-256 | PASS: no whitespace issues, expected paths ignored, master plan unchanged |
| Fresh `/tmp/promptpatch-module01-vmP8qo/venv`: `python -m pip install --no-cache-dir -r requirements-dev.txt`, `python -m pip install --no-cache-dir -e '.[dev]'`, `python -m pytest -q`, `python -m pip check` | PASS: complete clean-environment installation; **8 passed** in 1.27 seconds; no broken requirements |
| `git diff --cached --check` after adding the previously untracked master plan | Flags seven pre-existing Markdown hard-line-break spaces in the unchanged plan. Preserved original source; no new implementation whitespace errors |
| `git diff --cached --check -- . ':!PROMPTPATCH_CODEX_MASTER_PLAN.md'` | PASS: all foundation and documentation files pass whitespace check |

Local commit preparation initially hit the sandbox's read-only `.git/index.lock` restriction; authorized elevated staging succeeded. Local commits are authorized by the user; pushing remains the user's responsibility.

**Implemented:** installable src-layout package, safe environment configuration, CLI foundation, ignore rules, setup docs, and smoke/configuration/CLI tests.
**Tested:** eight tests include subprocess CLI runs from empty temporary working directories, no side effects for doctor/init, secret-safe output, and invalid-config handling.
**Pending:** database initialization/persistence (Module 02), all model/agent behavior, teacher approval, and real provider verification.
**Blocked:** no implementation blockers. The initial dependency network limitation was resolved by the authorized network-enabled retry. Key remains unset and provider not connected.

No API requests, database files/tables, graph, demo fixture, or later-module functionality created.

MODULE 01 COMPLETE — STOPPED. Awaiting: START MODULE 02

## Module 02 — SQLite persistent domain memory and versioned corrections

Status: **DONE**. The user's “do it” authorized Module 02 following the Module 01 handoff.
Starting repository was clean on `main`, with the Module 01 implementation present.
The plan, status, configuration, CLI, and foundation tests were inspected first;
no additional workspace `AGENTS.md` was found.

### Implemented

- `db.py`: atomic schema migration 1 using SQLite `user_version`, foreign keys,
  indexes, unique project/cycle/operation identities, and immutable-history guards.
  Initialization is repeatable, including concurrent calls, and refuses newer schemas.
- `repository.py`: stable caller-supplied project IDs and UUID record IDs; scoped
  APIs for projects, prompts, cases, policy proposals/approvals, cycles, risks,
  planner decisions, human decisions, tool operations/attempts, results, and audits.
- Every mutation and its audit records share one `BEGIN IMMEDIATE` transaction.
  All project-scoped record lookups and updates filter by project. Composite
  foreign keys prevent cross-project relationships even outside the API.
- Policy proposals do not activate themselves. An explicit actor is required for
  approval, old policies remain queryable, stale proposals are rejected, and new
  cycles select only the currently approved policy. Existing cycles keep their policy ID.
- Test references use actor-attributed immutable content revisions and canonical
  content hashes. Prompt Git SHA/hash values are stored as supplied; actual Git
  evidence verification is not implemented until Module 04.
- Risks have current-state rows plus preserved evidence in append-only audit history.
  Failure resolution and recurrence preserve first/last cycle provenance.
- Logical operations have stable unique keys. Failed attempts remain visible;
  saving a result and completing its operation are atomic. Replays cannot create
  duplicate completed results or duplicate cycle approval decisions.
- Domain exceptions distinguish missing/foreign records (same safe message), duplicate
  operations, invalid transitions, superseded policies, and general store errors.
- `promptpatch init` now creates the persistent domain DB and parent directory;
  retries preserve records. It never initializes checkpoints or contacts a provider.
  Doctor remains read-only. CLI errors avoid echoing paths/environment values.

### Files changed and design decisions

Added `src/promptpatch/db.py`, `src/promptpatch/repository.py`,
`src/promptpatch/errors.py`, and `tests/test_store.py`.
Updated `src/promptpatch/cli.py`, `tests/test_foundation.py`, `README.md`, and this file.

The only required Module 01 behavior change was replacing the authorized `init`
placeholder and its test; help and doctor text now describe current capability.
No dependency changes or folder-layout deviations were needed.

Schema adjustment: **one additional `operation_attempts` table** separates retry
attempt history from the unique logical operation/result. All eleven proposed
domain tables are present (12 total). SQLite triggers enforce immutable source
payloads and append-only decisions/results/audits. Risk summaries, active flags,
cycle state, and operation state are mutable; their transitions are audited.

Actor strings are attribution supplied by trusted local caller code, not authentication.
Policy/human approval CLI workflows await Module 07. Test-case revision creation
is an explicit developer-attributed store call, not a model-controlled correction.
The README documents archive/read-only semantics and retained history; no deletion
API or automatic expiry is introduced. Further redaction/security hardening awaits
Module 09. Checkpoint working memory remains separate and unimplemented.

### Commands and verified evidence

| Command / check | Actual result |
|---|---|
| Initial `git status --short` and existing file inspection | Clean tree; existing Module 01 functionality preserved |
| `.venv/bin/python -m pytest -q` after CLI/schema integration | PASS: existing 8 tests, with init test updated, in 1.55 seconds |
| `.venv/bin/python -m pytest -q` after initial store tests | PASS: 28 tests in 2.01 seconds |
| Final `.venv/bin/python -m pytest -q` | PASS: **32 passed in 2.42 seconds**, no failures |
| `.venv/bin/python -m pip check` | PASS: no broken requirements; no new dependencies |
| Inline Python CLI/database check using isolated temporary paths | PASS: real `promptpatch init` executed twice with a project write between; project retained; schema version 1; 12 tables; `PRAGMA integrity_check` = `ok`; zero `foreign_key_check` violations; no checkpoint DB created |
| `.venv/bin/promptpatch --help` | PASS: current init/doctor contract displayed |
| `.venv/bin/promptpatch doctor` | PASS: Python 3.14.4, SQLite 3.46.1, key/model unset; provider not connected; initialization available, readiness not claimed |
| `git diff --check` | PASS: no whitespace errors |

Tests prove close/reopen persistence **and retrieval in a new Python subprocess
without reseeding**. They also exercise policy v1→v2 supersession with pending v3,
stale proposals, cross-project reads/writes and raw composite FK rejection,
duplicate cycle/operation/approval protection, retained failed/completed attempts,
immutable history, audit timestamps/references, concurrent initialization, archive
write blocking, safe CLI errors, and rollback when an audit insert itself fails.
All model-like test records use explicitly synthetic offline values; they are not
live inference, actual extraction-validation results, or formal evaluation metrics.

**Implemented:** Module 02 domain storage and initialization.
**Tested:** 32 offline tests plus isolated real CLI/database checks above.
**Pending:** Module 03 fixtures; Git/provider integration, graph/checkpoints,
workflow approvals, demo cycles, reliability hardening, and formal evaluations.
**Blocked:** None in Module 02. Provider remains not connected; teacher approval
is still pending/unverified. No keys, model calls, or approval claims invented.

Next authorized step requires `START MODULE 03`. No Module 03 code/data was created.

MODULE 02 COMPLETE — STOPPED. Awaiting: START MODULE 03

## Module 03 — Curated cases and actual versioned local Git fixture

Status: **DONE**. The user's “do it” authorized Module 03 after the Module 02 stop.
Inspected the clean repository, plan's Module 03 instructions, existing store API,
package configuration, status, and ignore rules. Existing Modules 01–02 code is preserved.

### Implemented and design decisions

- Twelve fictional main-project cases cover integer/decimal extraction, both/one
  missing value, different wording, decimal zero, conflicting estimates, embedded
  untrusted instructions, distractor measurements, unsupported units, and explicit
  absence. One separate I01 case provides a disjoint isolation-project catalog.
- `SettlementExtraction` and `SettlementEvidence` in `models.py` define only the
  shared strict response shape and finite number/null types needed to validate
  fixture references. No evaluator, source-reading tool, or model adapter is implemented.
- References use source excerpts for numeric values and null evidence for missing
  or uncertain values. T08/T11 explicitly require clarification. Their expected
  status/reason/source reference are persisted in `fixture_case_imported` audit
  events linked to case IDs, alongside persisted ambiguity/category tags. This
  preserves the extraction JSON contract without changing Module 02's schema.
- Policy v1 defines fields, null behavior, evidence whitespace/substring rules,
  numeric tolerance, supported units, budget, and allowed/required IDs. Main budget
  4 with T01 required leaves 3 discretionary choices. Isolation has only I01 and budget 1.
- Candidate v2 changes exactly one rule: absolute tolerance 0.01 → 0.001 mm.
  It remains a file; seeding does not propose, approve, or activate this correction.
- `scripts/seed_demo.py` requires explicit `--approve-baseline` and `--actor` for
  fictional initial reference/policy setup. The actual seed used actor
  `fixture-bootstrap`; this records fixture initialization by the assistant, not
  teacher approval or a human release/prompt promotion decision.
- The script builds only its own empty fixture destination, with trusted tracked
  templates, three linear commits and tags, a marker, deterministic author/times,
  and raw prompt content hashes. It disables inherited Git routing/user hooks and
  rejects foreign/dirty/changed fixtures, remotes, unexpected local config, source
  ancestors, and Git-metadata destinations. No source text is executed.
- Reseeding verifies baseline identities, adds only missing rows, preserves IDs,
  timestamps, audit history, and later approved corrections. Separate durable
  transactions make partial DB imports resumable; no global all-or-nothing import
  is claimed. Partial Git creation is retained rather than deleted/reset automatically.
- Stable projects: `demo` (three prompt versions, twelve cases), `isolation` (own
  v1 prompt row and one case). Source SHA may be shared across projects while
  domain identities/policies/catalogs remain project-scoped.

### Files and runtime evidence

Added `samples/test_cases.json`, `samples/evaluation_policy_v1.json`,
`samples/evaluation_policy_v2.json`, `samples/prompts/v1.txt`, `v2.txt`, `v3.txt`,
`samples/README.md`, `scripts/seed_demo.py`, `src/promptpatch/models.py`, and
`tests/test_demo_fixtures.py`. Updated `.gitignore`, `README.md`, and this status file.
No dependency changes or existing-store repairs were required.

Created local, gitignored runtime files: `data/promptpatch.sqlite3` and
`samples/demo_git_repo/`. Only tracked templates/JSON/script/docs are committed;
runtime databases and nested Git metadata are excluded.

Verified fixture commits:

| Version | Actual Git SHA-1 |
|---|---|
| v1 | `514d7be901ecca503bd5832e83e7834537fe4eaa` |
| v2 | `e1e119c53028325d0dbd63deb4cf353b918ba644` |
| v3 | `1fed5a700edb94ddff2568531ee3f80f76f42ddc` |

The application repository HEAD before/after running the fixture script was
`2b704dd9761857cda4b5aad839ed8df6a8543479`. The script did not change parent history.
The separately authorized implementation commit is created only after verification.

### Actual commands/checks

| Command / check | Result |
|---|---|
| `.venv/bin/python scripts/seed_demo.py --help` | PASS: destination overrides and explicit baseline actor/approval documented |
| Inline Python temporary-directory seed/reseed smoke check | PASS: same three Git SHAs and fixture summary on both calls |
| Initial `.venv/bin/python -m pytest -q` | PASS: 60 tests in 6.50 seconds |
| Final `.venv/bin/python -m pytest -q` | PASS: **62 tests in 5.32 seconds**, no failures |
| `.venv/bin/python scripts/seed_demo.py --actor fixture-bootstrap --approve-baseline` (twice) | PASS: same summary/SHAs; demo 12 cases and isolation 1; v2 file only; zero model calls |
| `git -C samples/demo_git_repo log --oneline --decorate --all` | PASS: v1/v2/v3 tags on three distinct linear commits, HEAD at v3 |
| `git rev-parse HEAD` before/after seeding | PASS: application HEAD unchanged as recorded above |
| Inline Python repository/SQLite read-back | PASS: 2 projects, 4 prompt rows, 13 case rows, 2 approved v1 policy rows, 0 review cycles, 0 test executions, 36 audit events; `integrity_check` = `ok`; 0 foreign-key violations |
| `.venv/bin/python -m pip check` | PASS: no broken requirements |
| `git diff --check`, `git check-ignore` for fixture/DB, master-plan SHA-256 | PASS: clean whitespace, runtime paths ignored, master plan unchanged |

Tests verify every reference shape, numeric excerpt and source substring; unique
IDs and required tag coverage; exactly one changed candidate policy criterion;
three actual Git commits; prompt SHA-256/source identity; complete DB snapshots
unchanged under repeated seeds (including audit timestamps); preservation of later
corrections; parent repository preservation even with inherited Git routing;
refusal to overwrite existing files/dirty fixtures; approval and metadata-destination
guards; duplicate catalog rejection; seed/reseed from separate processes; and a
fresh Python process reading saved cases/policy without reimporting source samples.

**Implemented:** Module 03 fixtures and repeatable seed setup.
**Tested:** 62 offline tests and actual local Git/SQLite fixture creation/read-back.
**Pending:** Module 04 operational read-only tools; real provider, planner,
checkpoint/review workflow, three live review cycles, and formal evaluation.
**Blocked:** None. Teacher approval remains pending/unverified; provider remains
not connected. Prompt failure/recovery patterns are anticipated wording effects,
not observed live outcomes. T09 contains an attack example, not proof of resistance.

MODULE 03 COMPLETE — STOPPED. Awaiting: START MODULE 04

## Module 04 — Read-only Git evidence and scoped memory tools

Status: **DONE**. The user's “do it” authorized Module 04 following the Module 03
handoff. Initial tree was clean at `c96ec00` on `main`. Inspected the module plan,
status, configuration, domain schema/store API, fixture seeder, and README.
No additional workspace `AGENTS.md` found. No earlier module code/schema was changed.

### Implemented / design decisions

- `git_tool.py`: trusted per-project `RepositoryAccess` mapping, fixed read-only
  Git commands, full commit SHA validation, lexical/canonical path restrictions,
  project-owned snapshot registration checks, regular blob checks, UTF-8 decoding,
  raw SHA-256 verification, and typed prompt/diff evidence with provenance.
- Reads/compares never edit, stage, commit, checkout, or promote the evaluated repo.
  Defaults are 64 KiB per prompt, 128 KiB per diff, and 5 seconds per subprocess.
  Prompt size is checked before reading; stdout is streamed with a hard cap and
  child processes are killed/waited on after timeout or output overflow.
- Git environment routing/global config, optional locks, hooks/fsmonitor, lazy
  fetching, and replacement objects are disabled; diff disables external diff and
  text conversion. Full local non-bare repositories are supported. Linked worktrees,
  external object stores, and metadata/path escapes are explicitly rejected.
- Both diff snapshots must be registered to the requested project/path and match
  immutable stored hashes. No invented interpretation is returned, just the real
  bounded diff and source/version references. Embedded instructions remain data.
- `memory_tool.py`: bounded project-scoped risk/current state, immutable failure
  history, saved validation outcomes, developer decisions, approved policy
  corrections, and reference revision metadata. Each collection has a 1–50 limit,
  explicit truncation indicator, and combined 128 KiB result budget.
- Tags filter risk categories and tagged outcomes/reference revisions. Human
  decisions and policy corrections remain project-wide because they apply across
  categories. `open_only` affects risk/history selection. Raw model responses and
  full source bodies are excluded. History is bounded to the selected risk IDs.
- Active-policy lookup selects only approved current policy, with revision/source
  ID and parsed rules. Pending proposals never become active via retrieval.
- `tool_support.py`: read-only SQLite snapshots plus invocation/completion/error
  audit boundaries. Logs record call IDs, UTC timestamps, latency, safe error codes,
  and source record IDs; no source/feedback bodies, invalid inputs, or Git stderr.
  Memory retrieval/policy lookup additionally record `memory_read` events.
  Failed audit writes fail closed rather than returning success.
- Unknown projects cannot receive FK-scoped audit rows; archived projects forbid
  writes. Both fail without cross-project audit writes. Direct read-only store
  access to archived records remains available as documented in Module 02.

### Files changed

Added `src/promptpatch/git_tool.py`, `src/promptpatch/memory_tool.py`,
`src/promptpatch/tool_support.py`, `tests/test_git_tool.py`, and
`tests/test_memory_tool.py`. Updated README and this status document.
No new dependencies, schema migrations, or CLI commands were introduced.
Runtime SQLite audit rows are gitignored; evaluated Git metadata is unchanged.

### Actual checks / evidence

| Command / check | Result |
|---|---|
| `.venv/bin/python -m pytest -q` after initial tools | PASS: existing 62 tests in 4.98 seconds |
| Final `.venv/bin/python -m pytest -q` | PASS: **101 tests in 11.43 seconds**, no failures |
| Inline Python default-fixture tool exercise | PASS: actual v1/v2/v3 content/hash verification; real v1→v2 diff; traversal rejected; empty initial history correctly returned; approved v1 policy retrieved |
| Evaluated Git metadata SHA-256 snapshots before/after real tool exercise | PASS: all `.git` file contents unchanged |
| Audit read-back scoped to `demo` | 7 tool invocations, 6 successes, 1 deliberately rejected traversal, 2 memory-read events; 0 review cycles |
| `.venv/bin/python -m pip check` | PASS: no broken requirements |
| `git diff --check` | PASS: no whitespace errors |

Real source verification from the seeded fixture:

| Prompt | Bytes | Actual raw-content SHA-256 |
|---|---|---|
| v1 | 362 | `ce45d8d3eade5106baff29e06b8047b41821c0777cbdd541d6cceaec79521d8e` |
| v2 | 358 | `4e0cc181cedb93a45d4d8482edadd59cb035518940b0f93c76dfb3ccbe5fc229` |
| v3 | 762 | `a985dac72d9802f6d3da445330abf44789ea7cff9a2966002c40006df16f13ce` |

Actual v1→v2 diff: 594 UTF-8 bytes. No earlier review risks/outcomes/decisions or
corrections exist in the default fixture; all six returned historical collections
were correctly empty. Saved-history retrieval tests use separate synthetic offline
records, including regression/resolution, developer rejection, approved v2 with
pending v3, revised references, and another project's private evidence.

Tests also cover invalid refs/options, traversal/absolute/unsafe paths, missing
files, unknown commits, project registration/allowlist failures, hash mismatch,
UTF-8 errors, internal/external symlink rejection, output budgets, actual child
timeout termination, unsupported Git commands, no external diff/textconv execution,
embedded source instructions leaving policy/approval state unchanged, secret-safe
error/audit output, parameterized filters, bounded history/truncation, no foreign
memory, absent approved policy, unknown/archived projects, and audit-storage failure.

**Implemented:** Module 04 evidence and memory retrieval tools.
**Tested:** 101 offline tests and actual default-fixture Git/SQLite reads/audits.
**Pending:** Module 05 provider/executor/deterministic evaluator and later modules.
**Blocked:** None in Module 04. Provider is not connected; teacher approval remains
pending/unverified. No model outputs, live security claims, or formal evaluation
results are invented. Runtime tools need trusted local configuration and an
available writable domain audit store; their evaluated Git repo remains read-only.

MODULE 04 COMPLETE — STOPPED. Awaiting: START MODULE 05

## Module 05 — Provider adapter, executor and deterministic validator

Status: **BLOCKED**, not DONE. The user's “do it” authorized Module 05 after the
Module 04 handoff. Initial tree was clean at `458d2fc`. Inspected the module plan,
status, configuration, shared models, dependency pins, and runtime prerequisites.
Both `GEMINI_API_KEY` and `GEMINI_MODEL` were **not set**; values were never printed.
Provider authentication/quota/model support and live inference remain unverified.
Teacher approval remains pending/unverified. Module 06 was not started.

### Implemented (within authorized offline scope)

- `model_provider.py`: thin installed `google-genai` adapter with explicit key,
  Google endpoint, JSON Schema generation, purpose field, bounded settings,
  request timeout, response identity/version/usage/latency, and client cleanup.
  SDK retry attempts are 1 (no retries); automatic continuation and automatic
  function calling are disabled. Executor owns visible bounded retry attempts.
- Model purposes are explicit `candidate_execution` and `planner`. Returned
  metadata preserves purpose; executor rejects a planner response substituted for
  candidate execution. No planner decisions or LangGraph code are implemented.
- Default request budget: 2048 output tokens, temperature 0, optional seed unset,
  20-second SDK HTTP timeout, maximum 2 executor attempts (configurable 1–3), and
  0.2-second retry delay. The live smoke check uses exactly 1 allowed attempt.
- Safe error codes omit SDK/HTTP exception text and credentials. Provider timeout,
  quota, transport, invalid request, and incomplete/blocked response errors do not
  become extraction pass/fail results. No fallback is silently counted as live.
- `evaluator.py`: strict JSON/Pydantic response contract, duplicate-key/nonfinite
  rejection, Decimal absolute/relative tolerance, number/null comparison,
  source-substring and supporting number/unit checks with whitespace collapse.
  Distinct discrepancies include invalid JSON, missing key, invalid shape/type,
  incorrect numeric value, unjustified non-null, absent supporting quote,
  unsupported unit, and ambiguous source. No model judges the reference answer.
- Approved ambiguity/unsupported-unit metadata produces uncertainty for an
  otherwise correct response, not a clean pass. Invalid reference evidence or
  unsupported policy shape blocks before provider execution.
- `executor.py`: validates project/source/reference provenance, cycle-pinned
  approved policy, allowed test/catalog budget, response purpose/mode identity,
  and input/output limits; records real supplied usage and raw/parsed response
  with source IDs. Cost is left null, not invented. Completion/result writes use
  the existing atomic operation ledger. Completed keys reuse results, changed
  requests fail closed, failed attempt budgets survive repeated invocations,
  and interrupted external attempts require review rather than blind resubmission.
- Handwritten replay fixtures and `ReplayProvider` are explicitly separate from
  Gemini. Replay results persist `provider=replay`, `mode=replay`, fixture ID,
  empty usage, null cost, and zero live-model-call completion telemetry.
- `scripts/check_live_provider.py` performs a fixed v3/T02 integration smoke
  check, not an agent review/release. It uses a stable operation identity and
  safe preflight logging, and never falls back to replay. Missing configuration
  exits 2 before creating a cycle, operation, provider call, or test result.

### SDK verification and sources

Installed **google-genai 2.33.0**, **httpx 0.28.1**, and actual dependencies in the
project virtual environment. Direct runtime dependencies and 31 installed
development/runtime package pins were recorded. No model ID/version was guessed.

Consulted primary documentation: [Google SDK reference](https://googleapis.github.io/python-genai/),
[Gemini getting started](https://ai.google.dev/gemini-api/docs/get-started), and
[structured output](https://ai.google.dev/gemini-api/docs/structured-output).
Verified installed Client/generate_content signatures, HTTP timeout units, retry
attempt semantics, response fields, and continuation behavior using local inspection.
An exploratory lookup for `AutomaticContinuationConfig` raised AttributeError;
the installed field is boolean, and implementation uses `automatic_continuation=False`.
No guessed compatibility shim or deprecated provider import is used.

### Files changed

Added `src/promptpatch/model_provider.py`, `src/promptpatch/evaluator.py`,
`src/promptpatch/executor.py`, `scripts/check_live_provider.py`,
`samples/replay/module05_responses.json`, `tests/test_model_provider.py`,
`tests/test_evaluator.py`, and `tests/test_executor.py`.
Updated `pyproject.toml`, `requirements-dev.txt`, README, and this status document.
Existing domain schema, source fixtures, operational Git tools, and configuration
semantics are preserved. No new application CLI/review/graph functionality added.

### Actual commands and results

| Command / check | Actual outcome |
|---|---|
| Environment presence/package metadata probe | Key/model unset; SDK/HTTPX initially absent; no secret values displayed |
| `.venv/bin/python -m pip install --no-cache-dir google-genai` (network-enabled) | PASS: SDK 2.33.0 and dependencies installed |
| Installed-signature/source inspection | Verified request/response fields, milliseconds timeout, retries including first request; corrected boolean continuation lookup as noted above |
| `.venv/bin/python -m pytest -q tests/test_evaluator.py` | PASS: 34 deterministic tests in 0.21 seconds |
| Initial `.venv/bin/python -m pytest -q tests/test_model_provider.py` | 7 failed, 3 passed: test harness supplied a custom HTTP client whose lifetime the SDK deliberately leaves to its owner |
| Corrected SDK test harness | Mock transport is now injected into SDK-owned client options; cleanup acceptance assertion retained; no test skipped or criterion weakened |
| Repeated provider test file | PASS: 10 tests in 1.58 seconds, 1 SDK deprecation warning |
| Initial executor test file | PASS: 10 tests in 2.96 seconds, 1 SDK warning; further ambiguity/budget checks added before full run |
| `.venv/bin/python -m pip install --no-build-isolation -e '.[dev]'` | PASS: editable package updated against installed pinned dependencies |
| Final `.venv/bin/python -m pytest -q` | PASS: **158 tests in 15.78 seconds**, 1 SDK deprecation warning, no failing tests |
| `.venv/bin/python -m pip check` | PASS: no broken requirements |
| `.venv/bin/python scripts/check_live_provider.py` | **BLOCKED / exit 2**: key and model absent; no API call or test result created |
| Scoped SQLite read-back after live preflight | `demo`: 0 review cycles, 0 test executions; safe `provider_preflight_blocked` event records missing variable names only |
| `git diff --check` | PASS: no whitespace errors |

### Evidence and remaining acceptance

Tests exercise actual SDK request serialization through a **mock HTTP transport**;
all synthetic SDK usage/model-version fields are test values, not observed Gemini
performance. Replay executor tests persist to isolated real SQLite files and
verify fresh-process retrieval, retries with one completed logical result,
provider failures with zero extraction-result rows, strict purpose separation,
request-hash conflicts, interruption handling, cycle budget, and stored ambiguity.
These are **offline evidence only**. No live response or real provider result has
been persisted in the demo database, so Module 05's live acceptance is unmet.

Known warning: SDK imports Python's `_UnionGenericAlias`, deprecated toward Python
3.17; current verified interpreter is Python 3.14.4. Tests pass; warning not hidden.
SDK timeouts are HTTP request timeouts, not an independent hard wall-clock process
deadline. Sequential logical result deduplication does not guarantee exactly-once
external billing after network failure; concurrent workers are not supported here.
Broader hardening remains Module 09, and no claim of complete security is made.

**Implemented:** Module 05 adapter, replay provider, validator, executor, live check script.
**Tested:** 158 offline tests plus installed SDK signature/transport checks.
**Pending:** successful authorized real API call, actual returned model identity,
real usage/latency, persistent live result, then review of Module 05 acceptance.
**Blocked:** configure `GEMINI_API_KEY` and `GEMINI_MODEL` locally in the process
environment, then run `python scripts/check_live_provider.py` from that terminal.
Never send the key in chat. Resume with `FIX MODULE 05`; do not advance to Module 06.

MODULE 05 BLOCKED — STOPPED
