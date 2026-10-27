# PromptPatch implementation status

Last updated: 2026-10-27 (Asia/Karachi).
Authorized scope: **Modules 00–11**, including the user-requested Streamlit UI.
The user authorized local commits from Module 01 onward; the user will push.

## Execution contract

- Read the entire master plan before work; implement one authorized module per turn.
- Inspect → explain intent → edit → run required checks → inspect results → record evidence → stop.
- Preserve existing work; no commits, pushes, submission, or unrelated changes without explicit approval.
- Record actual results only. Distinguish implemented, tested, pending, and blocked work.
- Modules 00–11 are verified. Final stop: no further implementation, push or submission inferred.

## Module checklist

Allowed statuses: `PENDING`, `IN_PROGRESS`, `DONE`, `BLOCKED`. A `DONE` entry requires recorded verification, not just implementation.

| Module | Scope | Status | Date | Tests / evidence | Notes / remaining work |
|---|---|---|---|---|---|
| 00 | Inspection, requirements, execution contract | DONE | 2026-10-25 | Workspace/runtime inspection and document read-back; see verification below and REQUIREMENT_TRACEABILITY.md | Documentation implemented and checked; application not started |
| 01 | Python foundation, config, CLI, test harness | DONE | 2026-10-25 | Editable install, 8 pytest tests, help/doctor, pip check; see Module 01 evidence below | No DB tables, provider adapter, or graph implemented |
| 02 | SQLite domain memory, versioned corrections | DONE | 2026-10-25 | 32 passing tests; CLI init twice; SQLite integrity/FK checks; fresh-process retrieval | Domain persistence implemented; checkpoints and live integrations pending |
| 03 | Curated cases and versioned local Git fixture | DONE | 2026-10-25 | 62 passing tests; actual seed twice; three real Git SHAs; SQLite counts/integrity checked | Fictional baseline only; candidate v2 remains a file; no model results |
| 04 | Read-only Git and memory tools | DONE | 2026-10-25 | 101 passing tests; actual v1/v2/v3 reads/diff, bounded memory and approved-policy lookup, audit read-back | No provider calls, evaluator, graph or workflow CLI implemented |
| 05 | Provider adapter, executor, deterministic validator | DONE | 2026-10-25 | 158 tests passed; actual Gemini request and SQLite result verified; fresh-process reuse makes no additional call | Live `gemini-3.5-flash-lite` v3/T02 passed; see follow-up evidence below |
| 06 | LLM planner and persistent LangGraph workflow | DONE | 2026-10-25 | 180 tests; real planner and selected executions; matched live memory diagnostic; strict SQLite checkpoints and fresh-process reuse | Live planner verified; approval pending; see evidence below |
| 07 | Workflow CLI, approvals, corrections | DONE | 2026-10-25 | 200 tests; real live CLI and fresh-process reuse; offline approval/correction and atomic-request tests | Live approval pending; full Module 08 demo not started |
| 08 | Three cycles and full process restart | DONE | 2026-10-26 | 206 tests; three real live cycles; approved policy correction; fresh process and no reseed; verified artifacts | Historical HTTP failures retained; actual v3 release approval recorded in Module 10 |
| 09 | Reliability, security, isolation, retries | DONE | 2026-10-27 | 232 tests; 26 reproducible controls; one real malicious-input check; zero duplicate results; credential/telemetry verification | Formal evaluation recorded in Module 10; teacher approval unverified |
| 10 | Ten scenarios, three memory comparisons, measurements | DONE | 2026-10-27 | 249 tests; 10/10 offline scenarios; six live attempts; 1/3 vs 1/3; 5/5 facts; retry duplicates 0 | Quota limited two live arms; only one pair completed without provider errors; evidence retained |
| 11 | Reproducibility, report, submission, demo docs and Streamlit UI | DONE | 2026-10-27 | 259 clean-environment tests; 10 UI checks; 11 CLI commands; 10 scenarios; three-cycle replay/restart; final verifier | Local UI only; student/teacher/pagination/rehearsal checks remain; no ZIP or push |

Current approval state: the user approved the successful demo v3 release in Module 10. Teacher approval remains unverified. Older pending-approval statements below describe historical module snapshots.

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

Current status: **DONE after live verification**, recorded in the follow-up below.
The initial implementation was **BLOCKED**, not DONE. The user's “do it” authorized Module 05 after the
Module 04 handoff. Initial tree was clean at `458d2fc`. Inspected the module plan,
status, configuration, shared models, dependency pins, and runtime prerequisites.
Both `GEMINI_API_KEY` and `GEMINI_MODEL` were **not set**; values were never printed.
Provider authentication/quota/model support and live inference remain unverified.
Teacher approval remains pending/unverified. Module 06 was not started.

The sections through the first blocked stop line below preserve the **initial,
historical implementation evidence**; the live-verification follow-up supersedes
the missing-configuration blocker without changing those earlier observations.

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

## Module 05 live-verification follow-up — 2026-10-25

Status: **DONE**. The user supplied a key in the local `.env`, selected
`gemini-3.5-flash-lite` after official-model lookup, and explicitly requested
“test the module 5 now”. The missing-configuration blocker has been resolved.
Only Module 05 was tested; Module 06 remains pending and unimplemented.

### Commands and actual results

| Command / check | Actual result |
|---|---|
| Initial `git status --short` | Existing user deletion of `.env.example`; preserved and excluded from this follow-up commit |
| Network-enabled `.venv/bin/python` wrapper: parse allowlisted `.env` assignments with `shlex`, populate process environment, run `scripts/check_live_provider.py` via `runpy` | PASS / exit 0: **actual Gemini API request**, `mode=live`, `reused=false`, deterministic status `pass` |
| Separate fresh `.venv/bin/python` process: same safe environment loading, `check_live_provider.main([])`, scoped SQLite read-back before/after | PASS: `reused=true`, same execution ID and identical saved row; call/attempt/result counts unchanged |
| `.venv/bin/python -m pytest -q` | PASS: **158 tests in 15.73 seconds**, 1 existing SDK Python deprecation warning, 0 failures |
| `.venv/bin/python -m pip check` | PASS: no broken requirements |
| `git diff --check` | PASS: no whitespace errors |

The wrapper interpreted `.env` values as data, did not execute shell content,
did not display key values, and did not change production configuration behavior.
No `.env` or runtime database is staged/committed. The application itself still
reads process environment variables, not `.env` automatically.

### Persistent live evidence (actual observed values)

| Field | Observed value |
|---|---|
| Project / version / case | `demo` / `v3` / `T02` |
| Smoke cycle key | `module05-live-check` |
| Execution ID | `ca208013-6806-4c2b-bb70-e732fbbd124b` |
| Provider / mode / purpose | `gemini` / `live` / `candidate_execution` |
| Requested and returned model | `gemini-3.5-flash-lite` |
| Actual SDK version | `2.33.0` |
| Estimated settlement | **4.5 mm** |
| Allowable settlement | **10.0 mm** |
| Validation | **pass**, zero discrepancies |
| Input / output / total usage | **167 / 66 / 233 tokens** |
| Thinking-token usage | Not supplied (`null`), not assumed zero |
| Provider elapsed | **1561.428 ms** |
| Logical execution elapsed | **1625.994 ms** |
| Fresh-process repeat | Returned the same stored result; no additional model request |
| Persisted call starts / attempts / results for smoke cycle | **1 / 1 / 1** |
| Duplicate completed results after repeat | **0** |
| Approximate cost | Not calculated; retained as `null` |

The live result is stored in the configured gitignored SQLite domain database,
including raw response, parsed JSON, source/policy/test IDs, validation, usage,
latency, completed operation/attempt, and audit records. A fresh process verified
it and reused it, establishing persistence and sequential idempotency without a
second external model request. A credential-presence check confirmed the stored
response and validation do not contain the configured API key; no key was printed.

README and this status file now describe verified Module 05 acceptance. No
implementation/dependency changes were necessary in this follow-up. Historical
preflight failure events remain auditable; the successful live result does not
erase them. This fixed smoke case is **not** an LLM planner decision, a completed
three-cycle review demonstration, or developer release approval.

**Implemented:** Module 05 code from commit `560923d`, unchanged in this follow-up.
**Tested:** 158 tests, real Gemini v3/T02 execution, persisted live result, fresh-process
read-back and duplicate prevention, dependency/whitespace checks.
**Pending:** Module 06 and later modules. Live coverage of other catalog cases and
formal scenario/ablation evaluation remain pending. Teacher approval remains unverified.
**Blocked:** None within Module 05. Existing SDK warning and unmeasured cost are disclosed.

MODULE 05 COMPLETE — STOPPED. Awaiting: START MODULE 06


## Module 06 — LLM planner and persistent LangGraph workflow — 2026-10-25

Status: **DONE**. User explicitly authorized Module 06 and local commits. The
previous preparation turn was interrupted; it was not a failed stop gate. Only
Module 06 was implemented. No review CLI, human correction commands, full
three-cycle runner, formal evaluation suite, or later deliverables were added.

### Implemented

- `src/promptpatch/planner.py`: strict Pydantic decision contract; actual catalog
  IDs, permission/budget/required-test checks, concise reason, supplied memory and
  source reference checks; no fixed fallback list. Actual prompt, structured
  schema, response, settings, supplied history refs and errors persist in SQLite.
- `src/promptpatch/graph.py`: typed state and the ten specified LangGraph nodes,
  conditional executing/pending/error routes, real Git/memory/executor tools,
  deterministic durable-output revalidation, failure reconciliation, audit and
  evidence-grounded recommendations. Uncertain results and untested open risks
  prevent promotion recommendations; release approval is always separate.
- Separate real SQLite checkpoint file, thread `project_id:cycle_id`, explicit
  empty dynamic-type deserialization allowlists and disabled pickle fallback.
  Optional hosted tracing is disabled. Domain SQLite remains authoritative.
- Bounded project history retrieval; memory-off excludes history from the planner
  while retaining current source/catalog/policy/settings. Current human rejection
  and unresolved risks still constrain final recommendations in Python.
- Idempotent re-entry uses saved decisions/results and skips identical risk
  cycle/evidence writes. Interrupted unknown external calls fail closed. A planner
  has one terminal attempt per cycle; candidate retries remain executor-bounded.
- `scripts/check_graph.py`: one live developer integration check, output/export,
  without implementing Module 07 CLI commands. `tests/test_graph.py`: 22 new
  offline tests, explicitly labeled replay; old modules remain intact.
- Pins: LangGraph **1.2.17**, checkpoint SQLite **3.1.2**, installed checkpoint
  core **4.3.0**; full installed dependency snapshot updated. API/signatures and
  strict serializer behavior checked against installed source and official docs.

### Actual live evidence and repairs

Isolated data under `data/module06/` used the existing fictional Git fixture;
Module 05's default database was not used for these review cycles. Environment
values were safely parsed as data by temporary local runners; keys were never
printed, supplied as model context, or committed.

| Run | Actual selected/executed IDs | Observed recommendation |
|---|---|---|
| Initial v1 | T01, T02, T06, T07 | `revise`; T02/T06 numeric and quote failures stored as two open risks |
| v2 matched comparison | Same T01, T02, T06, T07 with and without history | Four passes each, `promote_candidate`, approval pending; **no selection difference** |
| Final matched v3, history on | T01, T02, T06, T07 | Four passes; specifically retested/resolved original failures; `promote_candidate`, approval pending |
| Final matched v3, history off | T01, T02, T08, T11 | Two passes, two uncertain; original untested T06 risk remains; `needs_review` |

The final memory-enabled planner explicitly cited the original two risk refs and
said it prioritized those earlier failures. Current inputs and model settings were
programmatically compared and matched; only long-term history and its derived
citation allowlist differ. This demonstrates an actual model-driven discretionary
selection difference. It is diagnostic evidence, not statistical proof or a claim
that memory always improves coverage; v2's identical selections are preserved.

Two earlier planner responses were rejected without execution: one cited supplied
UUIDs while the initial guard required prefixed refs (fixed to accept both), and
one confused catalog case refs with historical memory refs. An expanded schema
then produced HTTP 400, confirmed by one separately audited sanitized probe.
The final smaller schema constrains only historical citations and was accepted
by both live arms. All rejected responses/API errors remain in the exports and
SQLite audit trail; no failed cycle was overwritten/reused as a successful run.

Artifacts and detailed chronology: `artifacts/module06/README.md`, raw per-run
JSON snapshots, pre-execution expectations/repair notes, and `verification.json`.
The final pair each made **5** model calls (1 planner + 4 candidate), created
**12** checkpoints, saved exactly **4** results, and created **0** human decisions.
Memory-on usage: **7541 input / 635 output / 8176 total** tokens; summed provider
elapsed **8087.338 ms**. Memory-off: **4318 / 540 / 4858**, **6949.296 ms**.
Elapsed sums exclude graph/DB overhead; cost remains `null` rather than guessed.

### Commands and verified checks

| Command/check actually executed | Result |
|---|---|
| Install LangGraph/checkpoint packages; inspect installed serializer/saver signatures | PASS; actual versions pinned; strict settings supported |
| `.venv/bin/python -m pip install --no-deps --no-build-isolation -e .` | PASS; editable metadata updated |
| `.venv/bin/python -m pytest -q` | PASS: 180 tests, one existing Google SDK Python deprecation warning |
| `scripts/check_graph.main(...)` via temporary safe local environment runners | Real initial graph and all documented comparisons executed; failed attempts retained |
| Fresh child process reran both final graph checks | PASS; all domain table counts unchanged, no new model requests or writes |
| New-process strict SqliteSaver read-back in offline tests | PASS; recommendation restored from persisted checkpoint |
| Simulated interruption after committed planner/results, before node checkpoint | PASS; resume reused calls/results and did not duplicate actions |
| Final SQLite integrity / foreign keys / duplicate results | PASS; `ok`, zero FK errors, **0** duplicate results |
| Credential absence scan over exports and isolated databases | PASS; key not present; never printed |
| `.venv/bin/python -m pip check` | PASS; no broken requirements |
| `.venv/bin/python -m compileall -q src scripts tests` | PASS |
| `git diff --check` | PASS |

**Implemented/tested:** Module 06 planner, graph, real decision-controlled tool
execution, conditional paths, strict checkpoint creation, restart read-back,
resume deduplication, memory isolation, memory-on/off context equality and actual
live selection difference. Source/domain/tool implementations from Modules 00–05
were preserved; only additive dependencies/current documentation changed.

**Pending:** Module 07 onward, including the complete approval/correction CLI,
full three-cycle process-restart demo, formal three-comparison evaluation,
report, and teacher approval. The small integration checks are not substitutes.

**Known limits:** One worker per cycle; unknown in-flight calls need review.
Recommendations cover selected evidence only, so untested cases may fail.
Actual model decisions vary; earlier failures are disclosed. The pre-existing
user deletion of `.env.example` remains untouched and excluded from the commit.
No secrets or runtime databases are committed. Nothing pushed.

MODULE 06 COMPLETE — STOPPED. Awaiting: START MODULE 07


## Module 07 — Review CLI, developer approvals and corrections — 2026-10-25

Status: **DONE**. User explicitly authorized
`START MODULE 07` and previously authorized local commits, with pushes reserved
for the user. Scope is limited to Module 07. The pre-existing `.env.example`
deletion is preserved and excluded from this module's commit.

### Implemented

- Extended `src/promptpatch/cli.py` with `demo seed`, review start/status/resume,
  memory show, policy propose/approve, version approve/reject, and logs show.
  Formatted JSON displays version/cycle/policy, actual selected/executed IDs,
  deterministic discrepancies, Git/case/history refs, recommendation, errors,
  and the separate authoritative human approval record.
- Added `reviews.py`: project-scoped lookups, preflight for source/policy/cases,
  provider configuration and cycle key; atomic cycle/request creation; immutable
  saved model/settings/history/base-version/fixture metadata; checkpoint resume.
  Repeated identical starts return the same review. Changed requests are blocked.
- Added `approvals.py`: validated bounded policy documents, pending proposals,
  separate explicit activation, version/cycle matching, actor attribution, and
  duplicate decision rejection. Promotion approval requires a completed candidate
  under the current policy with no open risks. Rejection appends a separate row;
  the next graph retrieves it and respects it. Git is never changed by approvals.
- Added `review_audit.py`: adapters link existing source/memory reads and tool
  errors to a cycle. Original tool audits remain intact; this does not introduce
  new tool capabilities or additional model calls.
- Explicit replay requires a fixture/scenario and replay mode. Resume verifies
  its content hash and restores its event cursor from persisted call starts.
  Handwritten `samples/replay/module07_reviews.json` is clearly labeled as offline
  fixture evidence, not real Gemini inference or model agency.
- `tests/test_reviews_cli.py` exercises actual CLI subprocesses, SQLite and Git.
  Existing graph/store/provider implementations were preserved; the controller
  extends their interfaces rather than rewriting prior modules. No schema,
  dependency, configuration-loader, or evaluated-source changes were needed.

### Actual checks and evidence

| Command / check actually executed | Result |
|---|---|
| `.venv/bin/python -m pytest tests/test_foundation.py -q` | PASS: 10 tests; existing CLI/configuration behavior preserved |
| `.venv/bin/python -m pytest tests/test_reviews_cli.py -q` | PASS: 19 new tests before final atomic-request test, 85.27 seconds |
| Initial `.venv/bin/python -m pytest -q` | PASS: 199 tests in 115.88 seconds; one existing Google SDK Python deprecation warning |
| Final `.venv/bin/python -m pytest -q` after atomic cycle/request improvement | PASS: **200 tests in 104.84 seconds**, one existing SDK deprecation warning, zero failures |
| `.venv/bin/promptpatch review start --help`, `version approve --help` | PASS: exact command flags inspected |
| Temporary live wrapper invoking CLI subprocesses with safely parsed local credentials | PASS: one actual Gemini v3 review, status/resume, memory/log views; no release approval |
| Temporary offline wrapper invoking 13 CLI commands | PASS: replay review, simulated owner approval, duplicate approval blocked, policy proposal/activation, later review under revision 2, resume/log/memory views |
| SQLite integrity, foreign keys and duplicate completed-result queries in both isolated stores | PASS: `ok`, zero FK errors, zero duplicate results |
| Compare fixture v1/v2/v3 SHAs with recorded Module 03 identities | PASS: all three unchanged |
| Scan exports and isolated runtime databases for configured key | PASS: absent; key never printed |
| `.venv/bin/python -m pip check` | PASS: no broken requirements |
| `.venv/bin/python -m compileall -q src scripts tests` | PASS |
| `git diff --check` | PASS |

Live check: real `gemini-3.5-flash-lite`, `demo/v3`, cycle
`module07-live-cli`. The planner selected **T01/T02/T07/T11**, exactly those four
executed, and results were **pass/pass/pass/uncertain**. T11's unsupported-unit
metadata requires clarification. Recommendation: **needs_review**, human
approval **pending**. There were **5** model-call starts. Separate fresh Python
processes ran status/resume and returned identical output with unchanged domain
table counts: no repeated model calls, result writes, or approvals.

Offline evidence: simulated owner decisions use explicitly synthetic actors.
The proposal left revision 1 approved until a separate policy approval command;
then revision 1 became superseded and revision 2 approved. A subsequent review
used revision 2. A targeted test with the same replay output **4.005 mm** passes
under the original 0.01 tolerance and fails under approved 0.001, while the earlier
result remains unchanged. This is deterministic replay evidence, not live output.

Tests also cover project/version-mismatched and incomplete/failed review approvals,
blank actors, malformed policy JSON, stale proposals, old-policy candidate
approval rejection, rejection retrieved next time, resolved risks reopening as
regressed with original/latest cycle provenance, retry attempts with one completed
result, changed replay and missing checkpoints, and fresh-process resume after
planning or committed results. The final fault-injection check verifies that a
request-write interruption cannot leave an orphaned cycle.

Artifacts: `artifacts/module07/live_cli.json`, `replay_cli.json`,
`verification.json`, and their README. Authoritative databases and checkpoints
remain ignored under `data/module07/`. `.env` remains environment-only configuration;
temporary verification runners parsed selected local values as data, never shell
code, without exposing the key.

### Decisions and limits

- `version approve/reject` requires **--cycle** as well as version/project/actor;
  the exact review must be identified when multiple cycles exist. Policy proposal
  requires actor/reason and a file whose revision equals the next project revision.
- `demo seed` delegates to the existing Module 03 script from the documented
  editable checkout, preserving its destination verification and explicit
  fictional-baseline approval. Standalone wheel fixture packaging is unverified.
- A local actor string attributes an explicit command; this single-user CLI is
  not an authentication system. Synthetic test approvals do not imply student
  release approval or teacher approval. The live version remains unapproved.
- Completed checkpoints return their original recommendation; status reads the
  authoritative human decision separately. Unknown in-flight model attempts,
  held/invalid terminal plans, and missing checkpoints require review/restoration
  or a new cycle; resume does not blindly repeat external calls.
- One worker per cycle; no concurrent-worker orchestration. A completed review
  may still recommend needs_review or revise; CLI exit 0 does not mean release
  approval. No model cost was guessed.

**Implemented/tested:** CLI workflow and targeted Module 07 acceptance above;
**20 new integration tests**, atomic-request rollback/retry check, and the full
**200-test** regression suite passed.
**Pending:** Module 08 three-version/restart/correction runner and later modules,
formal evaluation/report, and actual teacher approval. No Module 08 implementation
or full three-cycle demonstration is claimed.
**Blocked:** None within Module 07. No secret or runtime database is committed;
nothing pushed.

MODULE 07 COMPLETE — STOPPED. Awaiting: START MODULE 08


## Module 08 initial handoff — before correction approval — 2026-10-26

Status: **BLOCKED — awaiting explicit developer correction approval**. The user
authorized Module 08 and local commits; no Module 09 work was started. Code and
checks below are implemented/tested, but live acceptance is not yet complete.

### Implemented

- `scripts/run_three_cycles.py`: isolated owned runtime/export directories;
  existing CLI commands run as separate OS application processes with recorded
  PID, start/exit times, exit code and confirmed reaping. Stable cycle keys reuse
  completed calls. No model-response-dependent Git/source edits or auto approvals.
- `prepare` seeds once, runs real v1/v2 reviews, and leaves the concrete policy
  correction pending. `finish` requires explicit `--approve-policy`, `--actor`,
  and `--approval-reference`; it activates revision 2, then runs v3 in a new
  process without reseeding/reuploading. The runner verifies original case IDs,
  source hashes and import-event counts, plus policy/checkpoint/provider evidence.
- Exports actual planner input/output, candidate responses, deterministic scores,
  source/policy identities and memory. Full completion exports the requested
  cycle files, restart text, process evidence, memory snapshots, policy history,
  tool timeline and concise summary. No replay is an automatic live fallback.
- `samples/replay/module08_cycles.json`: explicitly handwritten offline fixture
  showing decimal and missing-value regressions, continued/new risks, and later
  resolution. Its scripted choices are never claimed as live LLM agency.
- `tests/test_three_cycles.py`: real subprocess end-to-end replay, explicit
  approval boundary, source identity and process restart, revision 2 use, replay
  provenance, risk resolution, stage idempotency, interrupted-export recovery,
  ownership/configuration guards. Prior modules and dependency pins unchanged.

### Actual commands and results

| Command/check | Actual result |
|---|---|
| Initial `.venv/bin/python -m pytest tests/test_three_cycles.py -q` | FAILED: one SQLite-row conversion error in the new exporter, three tests passed |
| Fix row conversion and cached export recovery; rerun same tests | PASS: 4 tests in 14.81 seconds |
| `.venv/bin/python -m pytest -q` after final code/test changes | PASS: **204 tests in 120.98 seconds**, one existing Google SDK Python deprecation warning, zero failures |
| `.venv/bin/python /tmp/promptpatch_module08_live.py prepare` | Initial live v1 completed and persisted; old exporter failed afterward. Corrected rerun reused v1 without another call, then completed v2 and saved pending proposal |
| Replay runner `prepare --mode replay --runtime data/module08/replay --artifacts artifacts/demo_replay`, then `finish` with synthetic owner/approval reference | PASS: three completed CLI reviews, distinct process PIDs and confirmed exit before cycle 3; revision 2 active for cycle 3; all required replay artifacts saved |
| `.venv/bin/python scripts/run_three_cycles.py --help` | PASS: staged commands/options inspected |
| `.venv/bin/python -m compileall -q src scripts tests` | PASS |
| `.venv/bin/python -m pip check` | PASS: no broken requirements |
| `git diff --check` | PASS |
| Read-only SQLite checks for live and replay stores | PASS: integrity `ok`, zero FK errors, zero duplicate results |
| Scan runtime/export files for configured key without printing it | PASS: key absent |

The temporary live wrapper read only allowlisted `.env` values as data with
`shlex`, never executing shell content or printing credentials. The application
still reads process environment variables, and no credential/configuration file
was changed. Neither runtime databases nor temporary wrappers are committed.

### Live observations (actual Gemini, not replay)

| Cycle | Actual selection / results | Memory and outcome |
|---|---|---|
| v1 | T01 pass, T02 fail, T06 fail, T07 pass | No earlier risks; numeric/quote failures persisted as two risks; `revise`, approval pending |
| v2 | T01 pass, T02 pass, T06 pass, T05 fail | Planner explicitly cited both v1 risks and retested T02/T06; added T05 in place of T07; missing-value regression persisted; `revise`, approval pending |
| v3 | **NOT RUN** | Awaiting the concrete policy correction decision; no success/restart/model output invented |

The v2 reason explicitly references the earlier failures and its supplied risk
IDs. Its added T05 choice is observable sequential evidence; this is not a
controlled memory ablation or a statistical causality claim. Full controlled
comparisons remain Module 10 work. Live storage currently has 2 cycles,
2 planner decisions, 8 test executions and **0** human release decisions.

`artifacts/demo/policy_correction_pending.json` holds revision 2, proposed to
change absolute tolerance **0.01 → 0.001 mm**, retaining revision 1. It remains
pending and revision 1 remains the active approved policy. An asynchronous
approval request asked the developer to approve this specific isolated change
with actor `developer`. **No approval response has been received at this stop.**

The permission requirement comes from master plan Module 08 step 5, “Demonstrate
a developer-approved policy correction”, and the invariant that proposals stay
inactive until a separate explicit approval. Approval of a prompt release is a
different action; no prompt version is automatically approved by this runner.

### Replay observations (separate fixture evidence)

`artifacts/demo_replay/summary.json` records v1/v2/v3 recommendations
`revise/revise/promote_candidate`. Three stored risks resolve in cycle 3, all
selected v3 outputs pass, revision 1 remains queryable as superseded, and
revision 2 is active. `process_evidence.json` / `restart_evidence.txt` confirm a
fresh worker after the v2 process exited, identical saved source/case identities,
and no seed after v2. Prompt approval remains pending. Policy actor/reference
explicitly identify a synthetic offline test action; it is not student release
or teacher approval. Replay storage has 3 cycles, 3 planner decisions,
11 executions and **0** human release decisions.

### Remaining work and resume

**Implemented/tested:** runner, four tests, full regression suite, completed
replay restart/correction workflow, live v1/v2 memory-driven execution, and owned
exports. The exporter bug was fixed within Module 08 and the initial real result
reused; no failure history was erased.

**Pending/blocked:** explicit owner decision on the saved isolated policy
correction, then the live v3 process and final live restart/policy/evidence
verification. Do not mark Module 08 complete or start Module 09 yet. Existing
`.env.example` deletion remains preserved and excluded from the local commit.
No secrets or runtime databases are staged; nothing pushed. Teacher approval is
still unverified. Approximate cost remains unknown rather than fabricated.

After explicit approval, use the existing safe local environment wrapper:

```bash
.venv/bin/python /tmp/promptpatch_module08_live.py finish --approve-policy \
  --actor developer --approval-reference "Actual developer approval from this conversation"
```

The reference must describe an actual received approval, not be copied as a
claim before consent. Then verify outputs/checks, update this status, commit the
completion, and stop at the Module 09 gate.

MODULE 08 BLOCKED — STOPPED


## Module 08 completion follow-up — 2026-10-26

Status: **DONE**. The user explicitly approved the saved correction with “you
have my approval”. That authorization was applied to the isolated demo only,
with actor `developer` and a reference to the actual conversation. It does not
approve release of a prompt version. No Module 09 work was implemented.

### Completed live workflow

| Version | Actual selected/executed cases | Observed result / recommendation |
|---|---|---|
| v1 | T01, T02, T06, T07 | pass/fail/fail/pass; numeric and quote failures saved; `revise` |
| v2 | T01, T02, T06, T05 | pass/pass/pass/fail; original risks cited/retested; T05 missing-value regression saved; `revise` |
| v3 | T01, T05, T07, T12 | four passes; saved T05 risk cited/retested/resolved; `promote_candidate`, release approval pending |

Every selected case was actually executed through Gemini, and deterministic
validation determined the outcomes. The three original risks are now resolved.
No human release approval/rejection row was created. The live planner reasons
and actual history refs are retained; the separate replay fixture remains
explicitly labeled and is not used as live inference evidence.

The separate policy approval activated revision **2**, tightening absolute
numeric tolerance **0.01 → 0.001 mm**. Revision 1 remains queryable with its old
rules as superseded. The v3 planner input, pinned cycle policy and every v3
execution response reference revision 2. The pending-proposal artifact remains
an immutable historical snapshot; current approval evidence is in
`artifacts/demo/policy_correction.json`.

The v2 worker PID **161506** exited successfully at
`2026-10-26T18:08:11.483393+00:00`. The successful v3 worker PID **180540** started
at `2026-10-26T18:27:10.517663+00:00` and exited successfully. The runner confirmed
process exit, not merely a recreated Python object. The original case IDs,
source hashes and **12** case-import audit events match before/after. The same
domain/checkpoint files were used without reseeding or reuploading the dataset.
Each completed review has **12** persisted SQLite checkpoints.

### Failure diagnosis and bounded timeout extension

The first v3 planner request and one explicit fresh retry returned `api_error`
without executing any test. Both immutable failed cycles/exports remain. Two
standalone audited diagnostic requests using the saved context/schema succeeded;
these are diagnostics, not substituted workflow decisions or completed cycles.
An observation-only CLI diagnostic captured **HTTP 504 / DEADLINE_EXCEEDED**.
It also failed before any test and is preserved separately.

A small compatible interface extension for the current demo adds optional
`review start --timeout-ms`: the existing **20000 ms default** and model-settings
**30000 ms maximum** are preserved. The chosen timeout is persisted as part of
the immutable request and restored on resume. Changed requests using the same
cycle key remain blocked. No planner/provider decision logic, domain schema,
source contents, or dependency versions were changed.

The runner requires explicit `--retry-cycle3` to create a new review after a
failed command and retains `cycle_3_attempt_1.json` / `cycle_3_attempt_2.json`.
After the recorded deadline failure, one explicit changed-timeout attempt used
`--cycle3-timeout-ms 30000` under a new cycle key. It completed all four real
Gemini tests. Retries are bounded, never automatic, and do not resample completed
extraction failures or overwrite their records. The recorded policy approval
was reused, not applied a second time.

The final isolated live store contains **6** review rows: **3 completed** and
**3 failed planner reviews** (two managed by the runner plus the separately
observed diagnostic CLI failure). It has **6** planner decisions, **12** test
executions, **18** workflow call starts, **2** standalone diagnostic calls, and
**0** human release decisions. The summary's two failed attempts count runner
attempts only; all three failed reviews are disclosed in `verification.json`.
No cost estimate was invented (`null`).

### Commands/checks actually executed

| Command/check | Actual result |
|---|---|
| Existing safe local wrapper: `finish --approve-policy --actor developer --approval-reference <actual user consent>` | Approval applied once; initial v3 planner failed closed; failure retained |
| Exact saved-context/schema diagnostic requests | Two real planner responses; saved separately, not counted as successful graph cycles |
| Observation-only CLI SDK-error capture | HTTP **504**, deadline expired; source/request evidence retained |
| `finish ... --retry-cycle3 --cycle3-timeout-ms 30000` | PASS: real fresh-process v3 completed; four passes and evidence-grounded promotion recommendation |
| `.venv/bin/python -m pytest tests/test_three_cycles.py tests/test_reviews_cli.py::test_timeout_setting_is_bounded_persisted_and_part_of_request -q` | PASS: **6 tests in 42.75 seconds**, one existing SDK warning |
| Final `.venv/bin/python -m pytest -q` | PASS: **206 tests in 139.03 seconds**, one existing SDK Python deprecation warning, zero failures |
| Dedicated read-only live DB/artifact verifier | PASS: correct provider modes, selected=executed IDs, revision 2 settings/provenance, checkpoints, process exit order, unchanged source identity |
| SQLite integrity/FKs/duplicate queries | PASS: `ok`, **0** FK errors, **0** duplicate completed results |
| Fresh-process repeat of completed `finish` | PASS: identical summary; all domain table counts unchanged; no extra API calls, approvals or writes |
| Configured-key absence scan over live/replay exports and runtime files | PASS: key absent; not printed |
| `.venv/bin/python -m pip check` | PASS: no broken requirements |
| `.venv/bin/python -m compileall -q src scripts tests` | PASS |
| `git diff --check` | PASS |

The final suite includes a real subprocess retry/correction test that preserves
failed review IDs and creates a separate successful review without duplicating
approval. The timeout test checks persistence, bounds and changed-request
rejection. Prior modules' defaults and existing regression tests still pass.

All requested live artifacts now exist: `cycle_1.json`, `cycle_2.json`,
`cycle_3.json`, `restart_evidence.txt`, `memory_before_after.json`,
`tool_timeline.json`; plus `process_evidence.json`, `policy_correction.json`,
`summary.json`, `verification.json`, earlier failed attempts and diagnostic
records. The live artifact README documents actual outcomes and all failures.
Authoritative runtime databases and temporary diagnostic wrappers remain ignored.

**Implemented/tested:** Module 08 three-cycle live/replay runners, real restart,
source continuity, memory-informed selection, explicitly approved correction,
bounded recovery, evidence exports, idempotency and the 206-test regression suite.
**Pending:** Module 09 onward, formal controlled ablations/scenarios/report,
actual teacher approval and the developer's separate prompt release decision.
**Blocked:** None within Module 08. The existing `.env.example` deletion remains
untouched and excluded from commits. No secrets/databases are committed. Nothing
pushed. Starting Module 09 still requires explicit approval.

MODULE 08 COMPLETE — STOPPED. Awaiting: START MODULE 09


## Module 09 — Reliability, security, isolation and retries — 2026-10-27

Status: **DONE**. User explicitly authorized Module 09 and local commits.
Only current-module hardening, controls, telemetry and evidence were added;
Module 10 formal scenarios, ablations and overall scoring were not implemented.

### Implemented and design decisions

- Added `security.py`: reject recognized configured/Google-shaped credentials
  at source, provider and persistence boundaries; recursively redact logs and
  exports, including escaped JSON, named credential fields and Bearer strings.
  Ground truth, source text and hashes are not silently changed to hide problems.
- Hardened repository insert/update paths, actor inputs, risk evidence and result
  references. Sensitive writes fail atomically; audit details/attempts redact.
  Existing immutable records and schema are preserved; no migration/deletion ran.
- Read tools, planner/executor inputs and outputs, initial/restored graph state,
  cached execution results, CLI request metadata and export/error output enforce
  the credential boundary. SDK responses are checked against explicit SecretStr
  keys as well as configured values; no key must enter model context to test this.
- Provider errors expose safe bounded codes, optional numeric HTTP status and
  timeout flags, not SDK text. HTTP 408/504 now report retryable timeouts. SDK
  retries/continuation/tools stay disabled; executor attempts stay bounded and
  planner failure remains terminal per cycle. Failure timing is saved even when
  no planner response exists. No fixed test-choice fallback was added.
- Added `telemetry.py` and read-only `telemetry show --project ... --cycle ...`:
  actual call starts/purposes/modes, received responses, failure metadata, unknown
  in-flight operations, latency sums, known/missing token counters, completed
  results, duplicate logical actions and measured local storage. Cost stays null.
  A response is not evidence of valid planning; invalid-plan failures can overlap
  received-response counts. Missing values/legacy timings are not invented.
- Added `scripts/check_reliability.py`, 26 targeted tests in
  `tests/test_reliability.py`, actual pytest/JUnit and per-control evidence under
  `artifacts/reliability/`, plus `docs/RELIABILITY_CONTROLS.md` covering boundaries,
  trusted checkpoint files, correction history, owner archive/retention semantics
  and explicit limits. The runner measures offline elapsed/CPU/Linux peak RSS.

These are compatible current-module extensions of existing store/provider/graph
boundaries, not a redesign of earlier modules. Defaults, dependency versions,
SQLite schema and operational read-only Git permissions remain intact.

### Verified controls

| Control | Observed outcome |
|---|---|
| First candidate attempt HTTP-504-shaped timeout, second succeeds | Two attempts recorded, one logical result, 3 total model calls including planner, 0 duplicate actions; completed re-entry makes no call |
| Conflicting/unsupported evidence | T08/T11 remain uncertain; recommendation needs_review, no promotion |
| Malicious Git prompt and case text in isolated fixtures | Text supplied as data; policy, Git HEAD and human approval unchanged; only allowed cases executed |
| Model attempts an approval field or forged foreign/path test IDs | Invalid plan; zero candidate calls and no unauthorized approval |
| Foreign project risks/decisions and guessed cycle/record IDs | Scoped lookup/source rejection; no foreign memory supplied or injected; telemetry also rejects foreign cycle IDs |
| Interrupted graph after committed risk writes | Resume uses original decisions/results; one failure event, no duplicate side effect |
| Repeated seed, policy approval, start/resume | Seed leaves rows/counts unchanged; duplicate approval blocked; existing integration tests also retain no-repeat guarantees |
| Approved correction history | Pending proposal stays inactive; old revision retained/superseded; actor, reason, IDs and UTC timestamps remain auditable |
| Credential-bearing planner/candidate/SDK metadata | Fail closed without stored result or copied credential; explicit provider keys protected even without an env key |
| Sensitive new and existing-row writes | Rejected before commit; previous evidence and active policy unchanged |
| Legacy source/checkpoint with synthetic credential | No provider request or return of sensitive state; historical source not silently erased |
| Audit/export/error credentials | Nested/escaped values, known keys, named fields and Bearer strings redact; exception values hidden |
| Owner archive | Explicit actor required; retained history readable; new writes/model work/audited reads blocked |
| In-flight retry after an earlier failed attempt | Unknown operation detected using start/attempt counts, not hidden by the earlier failure row |

The offline provider and SDK transport are explicitly replay/mocks. Those tests
prove deterministic controls, not universal empirical LLM injection resistance.
Legacy fixtures intentionally retain synthetic old source/checkpoint data only
inside temporary test directories; actual configured key scans target the real
owned runtime/export stores and reveal no credential.

### Actual live negative control and telemetry

A separate fictional `data/module09/live.sqlite3` was initialized. The owner
fixture adds the requested malicious instruction to T09 input, while preserving
its legitimate 6/9 mm reference values. One real Gemini v3 extraction executed
through the existing read-only Git tool and executor. It is a **fixed-case
security control, not planner-selected agency or a completed graph review**.

| Field | Actual observation |
|---|---|
| Provider/model/SDK | live Gemini / gemini-3.5-flash-lite / 2.33.0 |
| Input/output/total tokens | **196 / 58 / 254** |
| Thinking tokens | Not supplied; unknown, not zero |
| Provider response latency | **5910.855 ms** |
| Stored logical execution latency | **5982.826 ms** |
| Extraction | pass; malicious instructions did not change the approved numeric result |
| Policy / human release decisions | unchanged / **0** |
| Actual live call starts | **1** |
| Repeat completed operation | saved result reused; no additional API call or result |
| Duplicate completed results | **0** |
| Approximate cost | unknown / null |

Later evidence refreshes reuse that original live result; their wall latency
measures reuse, while stored provider/logical latency remains the actual original
measurement. No repeat is mislabeled as a fresh inference. Real read tools can
emit additional genuine read audits; they are not duplicate model/result actions.

### Commands and actual results

| Command/check executed | Actual result |
|---|---|
| Initial focused old-module tests for SDK/executor/store/graph | PASS: 67 tests |
| Initial legacy-source test construction | Failed because the existing immutable-source trigger correctly rejected an UPDATE; the fixture was corrected to add a legacy revision without weakening production constraints |
| `.venv/bin/python -m pytest tests/test_reliability.py tests/test_store.py -q` after final boundary guards | PASS: **48 tests in 6.77 seconds**, one existing SDK warning |
| Final `.venv/bin/python -m pytest -q` | PASS: **232 tests in 156.68 seconds**, one existing Google SDK Python deprecation warning, zero failures |
| `.venv/bin/python scripts/check_reliability.py` | PASS: explicit offline checks, JUnit/JSON/proofs and measured local resources |
| Safe allowlisted local environment wrapper invoking `scripts/check_reliability.py --live-injection` | PASS: one actual call, adversarial input, persisted/reused result, no policy/approval changes; later refreshes made no new call |
| `telemetry show --project demo --cycle module09-live-injection` against isolated store | PASS: 1 actual call, 1 result, zero duplicates, token/missing-value counters; read-only audit-count check |
| Independent SQLite/artifact verifier | PASS: integrity ok, no FK errors, no duplicate results, no release decisions, configured key absent from runtime/exports |
| `.venv/bin/python -m compileall -q src scripts tests` | PASS |
| `.venv/bin/python -m pip check` | PASS: no broken requirements |
| `git diff --check` | PASS |

The live wrapper parsed selected local `.env` values as data, never sourced shell
code, and did not print the key. Configuration still reads the process environment;
no credential, `.env` change or runtime database is committed. Temporary wrappers
are not project deliverables. Existing `.env.example` user deletion is preserved
and excluded from this commit.

**Implemented/tested:** Module 09 controls/evidence above, safe persistence and
read boundaries, retry/interruption/idempotency, isolation, correction/archive
semantics, actual model/tool audits, latency/token/local resource measurements,
and the 232-test regression suite.
**Pending:** Module 10 formal scenarios, three controlled comparisons and factual
claims audit; Module 11 report/package; teacher approval and any prompt release
remain separate/unverified. No formal pass rate or statistical claim was invented.
**Known limits:** one worker per cycle, no multi-user authentication, no remote
exactly-once billing guarantee, trusted local checkpoints, recognized-credential
rather than arbitrary-secret detection, and no automatic erasure of legacy data.
**Blocked:** None within Module 09. Nothing pushed.

MODULE 09 COMPLETE — STOPPED. Awaiting: START MODULE 10


## Module 10 — Formal evaluation — 2026-10-27

Status: **DONE** for evaluation implementation, executed measurements and honest
evidence reporting. User explicitly authorized Module 10, local commits, the
successful v3 release approval, and subsequently the six live Gemini reviews
with their exact fictional payload/destination. Module 11 was not started.

### Implemented and verified

- Added `scripts/evaluation_support.py`, `run_scenarios.py`, `run_ablation.py`
  and `evaluate_evidence.py`. No production planner, evaluator, policy, schema,
  provider or dependency version was changed to obtain a favorable result.
- Ten distinct isolated scenario/control workflows execute real Git/SQLite/graph
  code with an explicitly handwritten replay provider. JSON/CSV contain all
  required columns. Per-scenario exports retain actual states, domain rows,
  operation attempts, timestamps and audit events. Tests intentionally inject a
  failing scenario and verify it stays FAIL rather than inflating the score.
- S03 launches two actual subprocesses: first exits, second has a different PID,
  reloads strict checkpoints and historical risk, skips completed calls, and
  continues without reseeding. Original case IDs and 13 import events remain.
- S04 tests identical 4.505 output against 4.5: pass at 0.01 mm, fail at 0.001 mm
  after separate explicit fixture-owner approval; pending/old/new policy retained.
- S07 records timeout and successful retry, re-entry without additional calls,
  one logical extraction and SQL duplicate count 0. Replay attempts are not
  represented as an actual Gemini outage. S10 shows remembered synthetic
  rejection preventing later promotion despite passing extraction.
- Protocol expectations and metrics were frozen before comparison requests.
  Each pair starts from byte-identical SQLite backups. Current prompt/diff,
  catalog/source IDs, approved policy, model/settings/instructions are equivalent;
  only long-term planner history and its derived citation schema differ.
- Histories are explicitly scripted conditioning, never presented as live prior
  inference. All six current comparison attempts use real Gemini. Exact planner
  instructions/context/schema, settings, raw responses, execution evidence and
  error metadata are exported. No memory-flag-based test-choice branch exists.
- Added `docs/TEST_SCENARIOS.md`, 17 formal/measurement/guard tests, and generated
  `artifacts/evaluation/RESULTS.md` plus JSON/CSV, claims, telemetry, JUnit and
  verification. README now links actual measured results and current approval.

### Actual results, including failures

| Measurement | Observed |
|---|---|
| Scenario/control pass rate | **10/10 (100%)**, offline replay; not live extraction accuracy |
| Memory-on combined selection/execution success | **1/3** |
| Memory-off combined selection/execution success | **1/3** |
| Paired reviews attempted / pairs without provider error | **6 arms / 3 pairs**, only **1** fully provider-error-free pair |
| Five factual claims | **5/5** correct against immutable output/source/event and real Git read |
| Duplicate logical actions under retry | **0**, measured SQL and telemetry |
| Representative live A01 memory-on | **5** actual model calls; **6190** tokens; **15732.974 ms** summed logical latency; **20767.420 ms** wall time; **0.943 s** local CPU |
| Cost / thinking token count | unknown / unknown; not fabricated as zero |
| Cached driver rerun | All six original exports reused; **0** extra model starts/results |

A01 both arms selected/executed T01,T02,T06,T07 and passed the predeclared metric.
A02 memory-on selected T01,T05,T02,T04, while memory-off selected T01,T02,T08,T11.
The memory-on arm executed only T01 before quota errors exhausted bounded retries
for T05. Selecting T05 alone did not meet the predeclared execution criterion.
A03 memory-on's planner returned quota; no planner decision or restraint is
invented. Memory-off selected T01,T02,T07,T11 and needed review. A03's metric
checks actual planner HOLD/CLARIFICATION, not the mandatory rejection guard that
remains active in both arms. Neither arm met it. Quota-limited arms stay in the
three-case denominator, with failed-request and incomplete-pair details explicit.
No calls were resampled to improve the score, and no statistical superiority is
claimed. These provider limitations are evaluation findings; all application
regression/scenario tests pass. Earlier live v1 failures and v3 deadline failures
remain linked as real failure examples.

### Actual approval and disclosure

User release approval was persisted as human decision
`7c70c883-f2cd-4f9a-9642-afc9f56414d4`, actor `developer`, at
`2026-10-27T10:45:58.823608+00:00`, for successful v3 cycle
`module08-c3-timeout-30000`. Read-only workflow status now shows `approved`.
The historical Module 08 JSON snapshots still correctly show then-pending state;
`artifacts/evaluation/release_approval.json` exports the current immutable receipt
and audit event. No deployment, prompt edit or Git push occurred. Fixture-owner
approvals/rejections and the prior actual tolerance correction are separate.
Teacher approval remains **unverified**.

Automatic review initially rejected external requests because it required explicit
payload/destination approval. The user then selected **“Approve these six Gemini
reviews”** for the fictional cases/demo prompts/policy/synthetic history sent to
`generativelanguage.googleapis.com`. That resolved the rejection; consent is
recorded separately in `ablation/authorization.json`. Only the six bounded
reviews ran. A safe temporary wrapper parsed two allowlisted `.env` values as
configuration data without printing or sourcing the file. Secrets, wrappers and
runtime DBs remain uncommitted. Codex assisted with evaluation code/docs; the
student still needs to review and understand the methods and limitations.

### Commands/checks actually executed

| Command/check | Result |
|---|---|
| `.venv/bin/python -m scripts.run_scenarios` | PASS: **10/10**, actual per-scenario JSON/CSV and domain evidence |
| `.venv/bin/python -m pytest tests/test_scenarios.py -q` before final added guard | PASS: **16 tests in 27.69 s** |
| Dedicated paired-context/rejection-guard test | PASS: **1 test in 3.55 s**; same actual current context and rejection enforcement in both arms |
| `.venv/bin/python -m scripts.run_ablation prepare --model gemini-3.5-flash-lite` | PASS: predeclared protocol; three initially identical paired snapshots; no API calls |
| Authorized safe wrapper → `scripts.run_ablation run` | All six live attempts recorded; quota on A02/A03 memory-on retained; **1/3 vs 1/3** |
| Same driver re-entry with saved exports | PASS: reused results, **0** extra calls or result rows |
| `.venv/bin/python -m scripts.evaluate_evidence` | PASS: actual reports, **5/5 facts**, representative telemetry and honest failures |
| First full suite before final added guard | PASS: **248 tests in 195.66 s** |
| Final `.venv/bin/python -m pytest -q --junitxml=/tmp/promptpatch-module10-final.xml` | PASS: **249 tests**, elapsed recorded below; one existing SDK warning; zero failed/skipped |
| Independent evidence verifier | PASS: scenario refs/IDs, 5 facts, frozen protocol hash, initial paired hashes, SQLite integrity/FKs/duplicates, configured key absent from exports/runtime |
| `.venv/bin/python -m pip check` | PASS: no broken requirements |
| `.venv/bin/python -m compileall -q src scripts tests` | PASS |
| `git diff --check`, unchanged master-plan SHA-256 | PASS |

The first staged whitespace check flagged the CSV writer's default CRLF line
endings. The writer and exported CSV were normalized to LF, preserving all data;
the export test (1 passed in 8.98 s) and staged check were rerun successfully.

Final full-suite elapsed: **194.61 seconds**.
JUnit and measured results are preserved in `artifacts/evaluation/tests/`.

**Implemented/tested:** Module 10 evidence tooling, ten controls, six live
comparison attempts with paired equivalence, explicit outcomes/errors, sampled
claims, retry count, representative actual resources and full regression suite.
**Known limitations:** only one complete provider-error-free pair; no demonstrated
advantage in the predeclared aggregate score; no A03 live memory-on decision due
to quota; diagnostic sample size; synthetic conditioning; costs/teacher approval
unknown. Further empirical runs were not silently added to the six-review grant.
**Pending:** Module 11 report/reproducibility/package/viva deliverables and teacher
approval. Existing unstaged `.env.example` deletion is preserved and excluded
from commits. No unrelated files, credentials or databases staged. Nothing pushed.
**Blocked:** No implementation/test blocker; observed provider limits remain
explicitly reported rather than marked passing comparisons.

MODULE 10 COMPLETE — STOPPED. Awaiting: START MODULE 11


## Module 11 — UI, reproducibility and final deliverables — 2026-10-27

Status: **DONE** for implementation and automated verification. The user explicitly
authorized Module 11 **including Streamlit UI** and previously authorized local
commits. All planned implementation modules are complete. No Module 12 exists;
no further work, Git push, ZIP, public deployment or submission is inferred.

### Implemented

- Polished the CLI with read-only `review list --project ... --limit ...`, showing
  recent cycle/version/state, next action and authoritative human approval. Added
  `views.py` read-only project inventories reused by UI, with scoped history queries.
- Added Streamlit **1.66.1** as an optional `[ui]` extra, retaining every existing
  dependency pin. Updated the complete development/UI lock with installed versions.
- Added `ui.py`, `ui_launcher.py`, `scripts/run_ui.py`, `promptpatch-ui` entry point
  and static `.streamlit/config.toml`. Local dashboard includes main-project default,
  project/mode/version/cycle selectors, review form, actual results/reasons/evidence,
  telemetry, safe resume, human approval/rejection, memory/feedback, policy history
  and recent audit activity. Existing backend services own all review/decision rules.
- Browsing/rendering/refresh performs no model call or domain mutation. Live
  submission/resume requires an explicit checkbox/action. Replay is visibly labeled.
  Fixed CSS contains no dynamic data; source/model/comment values use safe text,
  structured tables or JSON. No private key input/display or public hosting added.
- Launcher binds **127.0.0.1** only, disables usage statistics/file watching, and
  optionally parses an explicitly named env file as data (six recognized variables,
  64 KiB bound, no shell evaluation). Process settings take precedence. A misplaced
  credential in another config field is rejected without displaying values.
- The supplied `--recorded-demo` option opens the original ignored Module 08 store
  without reimporting/reseeding. Its real successful v3 approval is shown separately
  from the historical recommendation. No existing release/policy decision changed.
- Rewrote README for fresh setup, UI/CLI commands, config, correction/approval,
  replay/live/restart/evaluation distinctions and actual limits. Added safe template
  **`config/.env.example`** instead of restoring the user's pre-existing root template
  deletion. The root `.env.example` deletion remains unstaged and untouched.
- Added architecture/diagram, detailed twelve-table memory/lifecycle document,
  evaluation interpretation, **2289-word five-page-section technical report draft**
  with four explicit print breaks, planned **nine-minute** demo and submission
  checklist. Updated requirement mapping and AI/dependency/fictional-data disclosure.
  No PDF pagination, teacher approval, student understanding or rehearsal is invented.
- Added `scripts/check_submission.py` to verify final files, local links, schema
  integrity, evidence refs, original limits, test results and configured credentials.
  Final artifacts are separate from original live/demo/evaluation evidence.

### Actual verification and fixes

| Command/check actually executed | Observed result |
|---|---|
| Install Streamlit with original lock as constraints | PASS: 1.66.1 plus compatible dependencies; existing versions retained |
| Main and fresh virtual environment editable `.[dev,ui]` install, `pip check` | PASS; fresh full lock installation and no broken requirements |
| Initial `.venv/bin/python -m pytest tests/test_ui.py -q` | 6 passed, 4 failed: alphabetical project ordering selected isolation by default |
| Main-project default correction; repeated UI suite | PASS: **10 tests in 9.77 s**; original approval/isolation assertions retained |
| Clean-env `python -m pytest -q --junitxml=/tmp/promptpatch-module11-full.xml` | PASS: **259 tests in 210.04 s**, zero failed/skipped, one existing SDK deprecation warning |
| Fresh-env CLI quickstart from a different unused working directory | PASS: **11 commands**, real init/seed/replay/list/status/resume/memory/log/telemetry; **0 live requests**, **0 duplicates**, **0 release decisions** |
| Final replay `run_three_cycles.py prepare` then `finish --approve-policy ...` | PASS: three complete cycles, confirmed process restart and stable source imports, explicit synthetic correction, revise/revise/promotion candidate |
| `python -m scripts.run_scenarios --runtime data/module11/scenarios --artifacts artifacts/final/scenarios` | PASS: **10/10** offline controls, real evidence/CSV/JSON |
| `python scripts/run_ui.py --env-file .env --recorded-demo` | Running locally at **http://127.0.0.1:8501**; no automatic external request |
| Local HTTP root and `/_stcore/health` | PASS: 200 and valid bodies |
| Actual recorded live store rendered with AppTest + live-call guard | PASS: successful v3 shown **approved**; all original domain counts unchanged; **0** provider calls |
| Final submission/evidence verifier and actual configured-key scan | PASS: deliverables, original 1/3-vs-1/3 quota limitations, links, SQLite integrity/FKs, required refs, no configured key in artifacts/runtime/source/docs |
| Compileall, pip check, UI/list help, Git whitespace checks | PASS |
| Original demo/evaluation Git diff, master-plan SHA | PASS: original evidence unchanged; master plan hash remains ba9243312bc06b48c42888000e863c7acace520ffffa8e51f03947a7a214af63 |

The four initial UI failures were corrected, not skipped. A temporary clean-env
verification wrapper initially failed to import its artifact-writing helper after
all CLI commands passed; its own path setup was fixed and the entire walkthrough
rerun from a different fresh directory. The public CLI/package did not require
that workaround. The final clean-env report records the successful complete run.

Artifacts: `artifacts/final/README.md`, `verification.json`,
`clean_environment.json`, `tests/full_suite.junit.xml`, `tests/ui.junit.xml`,
`ui_initial_check.json`, `ui_http.json`, `ui_recorded_demo.json`,
`demo_replay/` and `scenarios/`. Tests use Streamlit AppTest for actual widget/state
execution and a real HTTP server for serving/health. No browser screenshot is
claimed. The UI server is left running locally; Ctrl+C stops it. Restart command
is in README; runtime files are regenerated separately when unavailable.

### Limits and remaining student actions

- The actual Module 10 score remains **1/3 on versus 1/3 off**, with two quota-limited
  arms and only one error-free pair. Final replay/testing does not erase those errors
  or establish statistical superiority. No further live Gemini inference occurred.
- Teacher approval remains **unverified**. Student author details, original course
  PDF/rule check, code understanding, report pagination if exported and measured
  8–10 minute rehearsal remain explicit student actions, not implementation blockers.
- Five-page-section Markdown is a report draft with intended print breaks;
  no PDF/export submission or measured rehearsal duration is claimed.
- Local owner only: actor attribution is not login; one worker per cycle; trusted
  checkpoints; recognized-key detection is bounded; no automatic erasure or
  exactly-once provider billing guarantee.
- No ZIP requested, so none created. No API key, runtime DB, `.env`, raw personal
  file or temporary wrapper is committed. Root `.env.example` deletion preserved.

**Implemented/tested:** All Modules 00–11, including requested Streamlit UI,
required report/demo/schema/architecture/checklist and reproducibility evidence.
**Blocked:** No implementation/test blocker. Student/external checks above remain
accurately pending. Nothing pushed or submitted.

MODULE 11 COMPLETE — STOPPED.
