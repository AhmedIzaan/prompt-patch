# PromptPatch

Persistent prompt regression reviews with evidence, memory and human release
approval. The fictional task extracts estimated/allowable settlement measurements;
it is a software test fixture, not engineering advice.

The CLI and local Streamlit dashboard use the same LangGraph, SQLite and approval
services. **All Modules 00–11 are implemented; 259 tests pass**, including ten UI
checks, verified in a clean environment. Current implementation and final checks are tracked in
[IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md). Teacher approval remains
unverified; student review and final submission are separate actions.

## Setup

Supported/verified platform: Linux, **Python 3.14** (originally 3.14.4), SQLite
3.46.1 and Git. Other Python versions are not verified. Start from a checkout:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install --no-build-isolation -e '.[dev,ui]'
.venv/bin/python -m pytest -q
.venv/bin/promptpatch --help
.venv/bin/promptpatch doctor
```

`requirements-dev.txt` is the complete installed development/UI lock; direct
versions are in `pyproject.toml`. UI is an optional extra for CLI-only installs.
Final [clean-environment and test evidence](artifacts/final/README.md) is in
`artifacts/final/`. `doctor`
checks local configuration only; it does not claim provider/database readiness.

## Start the UI

```bash
.venv/bin/python scripts/run_ui.py --env-file .env
```

Open **http://127.0.0.1:8501**. The launcher explicitly parses the named env file
as configuration data, never shell code. Existing process variables take
precedence. If you have no `.env`, copy `config/.env.example` first and keep its
replay mode for offline testing. Preserve an existing `.env`; never commit a key.
The pre-existing local deletion of the root template is preserved; the documented
safe template is now under `config/`.

- Initialize/load fictional demo data with the explicit setup form if needed.
- Select a project, browse recent reviews and inspect selected tests, results,
  evidence, errors, memory/feedback, policy history and audit timeline.
- Create or resume a review explicitly. Replay uses handwritten fixtures and makes
  no provider calls. Live mode requires the configured key/model and explicit
  submission of the review data to Gemini; browsing never starts inference.
- Record a release decision only after inspecting the exact completed review.
  The existing backend guards apply. Policy correction approval remains a separate
  CLI action; the UI shows pending/current/superseded rules.

To view the original recorded live store, if its ignored runtime files are still
available locally:

```bash
.venv/bin/python scripts/run_ui.py --env-file .env --recorded-demo
```

This selects `data/module08/live/memory.sqlite3` and its checkpoint file; it does
not seed, import, create a release or make a provider call. Committed JSON artifacts
remain inspectable when ignored runtime DBs are unavailable. For an isolated
key-free workspace:

```bash
PROMPTPATCH_MODE=replay \
PROMPTPATCH_DB_PATH=data/ui-demo/domain.sqlite3 \
PROMPTPATCH_CHECKPOINT_DB_PATH=data/ui-demo/checkpoints.sqlite3 \
PROMPTPATCH_DEMO_REPO=data/ui-demo/git \
.venv/bin/python scripts/run_ui.py
```

The server binds loopback and disables usage statistics. It is a trusted local
owner tool without multi-user authentication. One worker per review cycle is
supported. Do not expose it publicly. Stop with Ctrl+C. A different local port can
be selected with `--port 8502`.

## Offline CLI walkthrough

The CLI reads process environment only; it never automatically loads `.env`.
Use these settings in the same terminal, with previously unused runtime paths:

```bash
export PROMPTPATCH_MODE=replay
export PROMPTPATCH_DB_PATH=data/quickstart/domain.sqlite3
export PROMPTPATCH_CHECKPOINT_DB_PATH=data/quickstart/checkpoints.sqlite3
export PROMPTPATCH_DEMO_REPO=data/quickstart/git
.venv/bin/promptpatch init
.venv/bin/promptpatch demo seed --actor developer --approve-baseline
.venv/bin/promptpatch review start --project demo --version v3 --cycle first-review \
  --replay-file samples/replay/module07_reviews.json --replay-scenario pass_v3
.venv/bin/promptpatch review list --project demo
.venv/bin/promptpatch review status --project demo --cycle first-review
.venv/bin/promptpatch review resume --project demo --cycle first-review
.venv/bin/promptpatch memory show --project demo
.venv/bin/promptpatch logs show --project demo --cycle first-review
.venv/bin/promptpatch telemetry show --project demo --cycle first-review
```

Replay is a deterministic control, not fresh LLM agency. Seeding approves only
fictional baseline references under the named actor and is idempotent. Status,
review list and telemetry do not invoke the provider. Logs without `--cycle` also
include project-wide policy and human events.

A cycle key identifies one immutable request. Repeated identical start/resume
reuses durable results and separate SQLite checkpoints. Keep both original DB
files, mode, Git fixture and saved configuration. Unknown in-flight API requests
fail closed; a terminal failed/held planner is not automatically resampled.
Changed requests require a new cycle key. Review completion is different from
release approval. Exit codes: 0 success/readable status, 1 execution/input failure
or incomplete review needing attention, 2 argument/configuration error. A completed
review may validly recommend revision or contain uncertain evidence.

## Live execution and configuration

Provide an authorized `GEMINI_API_KEY` privately and set `GEMINI_MODEL` to the
verified alias **gemini-3.5-flash-lite**. Switch `PROMPTPATCH_MODE=live` deliberately.
The selected prompt/diff, fictional cases, policy and relevant memory are sent to
Google Gemini at `generativelanguage.googleapis.com` on an explicit review action.
A key authenticates the request and is excluded from prompt context and exports.
No provider call is necessary for setup, browsing, replay or tests.

```bash
.venv/bin/promptpatch review start --project demo --version v3 --base-version v2 \
  --cycle live-review --timeout-ms 30000
```

The example assumes live variables in the invoking process, available quota and
already seeded sources. Default timeout is 20000 ms; allowed range 1000–30000.
Planner attempts are terminal per cycle. Extractions use bounded retries; no
silent replay fallback or loop retries until a favorable answer. Quota and deadline
failures are retained. One review selects at most four tests under fixture policy.

| Environment variable | Default / purpose |
|---|---|
| GEMINI_API_KEY | Unset; secret; needed only for live model actions |
| GEMINI_MODEL | Unset; verified alias above, provider response metadata retained |
| PROMPTPATCH_MODE | live; explicitly set replay for offline use |
| PROMPTPATCH_DB_PATH | data/promptpatch.sqlite3; authoritative domain store |
| PROMPTPATCH_CHECKPOINT_DB_PATH | data/checkpoints.sqlite3; separate working checkpoints |
| PROMPTPATCH_DEMO_REPO | samples/demo_git_repo; registered read-only prompt source |

## Corrections and human release decisions

Inspect the concrete change and exact review before executing owner actions:

```bash
.venv/bin/promptpatch policy propose --project demo \
  --file samples/evaluation_policy_v2.json --actor developer \
  --reason "Tighten numerical tolerance after review"
.venv/bin/promptpatch policy approve --project demo --revision 2 --actor developer
.venv/bin/promptpatch version approve --project demo --version v3 \
  --cycle first-review --actor developer
# Or reject a completed review instead:
.venv/bin/promptpatch version reject --project demo --version v3 \
  --cycle first-review --actor developer --comments "Explain the issue"
```

These are alternative examples, not a script to approve and reject the same cycle.
A proposal requires its revision to be the next revision. It remains inactive until
separately approved; old criteria remain queryable. Release approval requires a
completed promotion candidate under the current policy with no open risks, and
one immutable human decision is permitted per cycle. Actor text is attribution,
not authentication. Neither action changes Git, deploys, pushes, or proves teacher
approval. The actual successful live v3 approval is recorded in
[release_approval.json](artifacts/evaluation/release_approval.json).

## Three cycles and explicit restart

The staged runner launches separate CLI processes and preserves original cases:

```bash
.venv/bin/python scripts/run_three_cycles.py prepare --mode replay \
  --runtime data/three-cycles-replay --artifacts artifacts/three-cycles-replay
.venv/bin/python scripts/run_three_cycles.py finish --mode replay \
  --runtime data/three-cycles-replay --artifacts artifacts/three-cycles-replay \
  --approve-policy --actor synthetic-demo-owner \
  --approval-reference "Synthetic offline demonstration only"
```

Use unused output/runtime directories. These approvals are synthetic replay
fixture actions. The same staged live runner is documented in
[artifacts/demo/README.md](artifacts/demo/README.md); use it only with authorized
payloads/provider access and an actual separately reviewed policy correction.
Original live evidence shows v1/v2/v3 revise/revise/promotion candidate, real
restart, unchanged sources and approved tolerance 0.01→0.001 mm. Failed planner
attempts remain recorded. The later actual v3 human approval is a separate receipt.

## Evaluation, final checks and submission

```bash
.venv/bin/python -m scripts.run_scenarios \
  --runtime data/scenarios-rerun --artifacts artifacts/scenarios-rerun
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
```

All **10/10 offline control scenarios** passed in Module 10; **5/5 factual claims**
were checked and retry duplicates were **0**. Six live reviews attempted three
memory pairs: **1/3 with history and 1/3 without**. Quota limited A02/A03 memory-on;
only one pair completed without provider errors. Histories were scripted
conditioning, current comparison calls live. No aggregate/statistical advantage
is claimed. Current source alone can suggest regressions. Monetary cost and absent
thinking-token counts remain unknown. See the exact protocol and actual outputs:

- [Architecture](docs/ARCHITECTURE.md), [memory schema/lifecycle](docs/MEMORY_SCHEMA.md)
- [Scenarios and ablation commands](docs/TEST_SCENARIOS.md), [results](docs/EVALUATION_RESULTS.md)
- [Five-page-section technical report draft](docs/TECHNICAL_REPORT.md)
- [Nine-minute demo script](docs/DEMO_SCRIPT.md), [submission checklist](docs/SUBMISSION_CHECKLIST.md)
- [Control/security limits](docs/RELIABILITY_CONTROLS.md), [requirement mapping](docs/REQUIREMENT_TRACEABILITY.md)

Keep source snapshots, long-term history and working checkpoints distinct. Tools
cannot write the evaluated Git repository. Local archive retains history and
blocks new work; no automatic deletion or arbitrary-secret protection is promised.
Runtime DBs, keys, caches and raw logs stay ignored. No ZIP, push or submission is
performed automatically.

Codex assisted with planning, implementation, debugging, tests, documentation and
evaluation tooling. The student must review, understand and explain every submitted
component. Fixtures are fictional project data; no external dataset was imported.
Pinned upstream dependencies provide SDK/graph/UI functionality and retain their
licenses. Teacher approval, author identifiers, report pagination if exported and
measured demo rehearsal remain student verification tasks.
