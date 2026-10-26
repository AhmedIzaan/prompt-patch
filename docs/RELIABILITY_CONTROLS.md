# Module 09 reliability and security controls

The application remains a local, single-owner prototype. These controls apply to
its explicit source, provider, persistence, checkpoint, CLI and export boundaries.
They do not establish universal prompt-injection resistance or authenticate an
actor string. Module 10's formal scenarios/controlled ablations remain pending.

## Retry and interruption rules

Candidate execution has a stable project-scoped operation key and request hash.
Each bounded attempt records start, error/timeout, safe HTTP status, elapsed time,
and completion. The first timeout and second success yield two attempt records
and one immutable logical test result. Re-entry returns that result. It does not
retry a nonretryable failure, exceed the saved attempt budget, or silently change
input/settings. An unknown in-flight external call fails closed: provider-side
exactly-once billing cannot be guaranteed after a crash.

A planner has one terminal attempt per cycle. A failure or invalid decision stays
`needs_review`; no fixed list is substituted as model agency. Failure timing and
safe HTTP status are retained even when no response/test result exists. HTTP
408/504 are classified as retryable timeouts; other retryable statuses remain
bounded by the executor. SDK retries/automatic continuation/tool calls stay off.

A committed result, planner decision or failure-memory update is reused after an
interruption before the next graph checkpoint. Repeating start/resume/seed and
attempting duplicate policy/human decisions do not duplicate logical actions.
Read/audit events can legitimately repeat; those are not duplicate test actions.
The current implementation supports one worker per cycle, not concurrent workers.

## Untrusted content and isolation

Git contents, case inputs, memories/comments and provider output are data.
The planner can select only actual policy-allowed local case IDs, with the saved
budget/required tests and supplied evidence refs. Extra action fields, foreign
IDs and paths posing as test IDs fail closed before candidate execution. The
model cannot choose a project/repository/path, activate a policy, approve a
release, or execute arbitrary code. Operational Git tools are read-only.

Deterministic validation checks JSON shape, number/null values, supporting quotes
and approved tolerance. Ambiguous/conflicting/unsupported-unit source metadata
requires uncertainty; a provider's confidence cannot establish acceptance.

Every domain lookup and telemetry query is project-scoped; composite references
also enforce ownership. Caller-guessed foreign record/cycle IDs and foreign
source refs are rejected without supplying another project's history. This is
data partitioning for a local owner, not a multi-user authentication boundary.

## Credentials and immutable evidence

`security.py` recognizes configured Gemini/Google keys and Google-shaped keys.
New source/result writes and updates reject recognized credential material.
Read tools, direct executor inputs, graph context/restored state, and provider
responses fail closed before propagation/persistence. Explicit provider keys are
checked even if supplied as SecretStr without an environment variable.

Audit details and CLI/export snapshots redact configured values, escaped JSON
forms, recognizable keys, named API-key/access-token/authorization fields and
Bearer strings. Provider exceptions retain safe codes/statuses, not raw SDK
messages or credentials; invalid model-settings errors hide input values.

Authoritative source text, hashes and numeric references are not silently
rewritten to make validation pass. Legacy records/checkpoint files are not
migrated or erased automatically. If sensitive legacy evidence is encountered,
model work and return of sensitive state stop; owner review/correction is needed.
This is a bounded credential guard, not general-purpose secret detection for all
possible unknown credential formats or protection against an owner reading their
own raw SQLite/Git files. Existing trusted checkpoint-file requirements remain.

## History, archive and deletion

Approved corrections retain prior policy rows and immutable proposal/approval
events: old/new rules, reason, actor, IDs and UTC timestamps. A proposal is not
active until a separate explicit owner action. Duplicate/stale approvals fail.

The owner can archive a project through the existing repository API:

```python
from pathlib import Path
from promptpatch.repository import Repository
with Repository(Path("data/promptpatch.sqlite3")) as store:
    store.archive_project("demo", actor="developer")
```

Archive is an audited owner action. It blocks new writes, review/model execution
and audited tool reads. Existing domain status/timeline/telemetry can still be
inspected through read-only APIs. Archival retains source revisions, outcomes,
approvals, risks and checkpoints; it is not physical deletion.

There is no automatic pruning, individual-project erase or deletion tool. Any
physical removal of a store/checkpoint and its exports/backups is a separate,
explicit owner operation affecting everything in those files. This module does
not remove user data. Export copies and Git history have independent retention;
editing a source revision does not erase its old history.

## Measurements and reproduction

```bash
python scripts/check_reliability.py
# Optional one bounded real Gemini adversarial extraction; needs local variables:
python scripts/check_reliability.py --live-injection
PROMPTPATCH_DB_PATH=data/module09/live.sqlite3 promptpatch telemetry show \
  --project demo --cycle module09-live-injection
```

The runner owns `data/module09/` and `artifacts/reliability/` and refuses unowned
nonempty destinations. It saves actual pytest/JUnit output, per-control evidence,
local CPU/peak-RSS timing and an optional fixed-case live check. Live calls are
not needed by unit tests; replay/mocked SDK fixtures are explicitly labeled.
The live check is not planner selection or a completed graph review.

`telemetry show` is read-only. It reports started `MODEL_CALLS` by purpose/mode,
received provider responses, failed audit events, unknown in-flight operations,
observed logical/attempt/provider latency sums, token counters and missing-value
counts, completed tests, duplicate actions, and actual database storage sizes.
A received response can contain an invalid plan; it is not a successful agency
claim. Latency sums are not end-to-end wall time; missing old timings stay marked.
Replay tokens and absent thinking usage stay unknown, not zero. Duplicate count
means extra completed results per logical operation key plus extra human rows per
cycle, not duplicated HTTP billing. Cost stays null without a verified price.

The live control records the original persisted model latency/usage separately
from this invocation's wall time and reuse flag. Repeating it reuses the saved
result, not a fresh API request. See `artifacts/reliability/README.md` for actual
observations and limits. No scenario pass percentage or three-way ablation is
claimed by Module 09.
