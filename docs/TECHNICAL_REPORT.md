# PromptPatch: persistent memory for prompt regression reviews

**Technical report draft — 27 October 2026.** Student author: complete identifying
details before submission. Five page sections below use explicit print breaks;
target A4, 11 pt, 18 mm margins. Actual PDF pagination must be checked if exported.
This Markdown draft is not a claim that a PDF was generated or submitted.

## Page 1 — Problem, scope and design decisions

Prompt updates can repair one extraction failure while introducing another. A
developer who only checks the newest example may forget a previous decimal error,
absent-field mistake or rejected release. PromptPatch supports this recurring
workflow: review a versioned prompt, retrieve relevant historical failures, choose
regression tests, execute a model, validate outputs, save the outcome and present
an evidence-grounded recommendation for human review. Its purpose is repeated
regression triage, not a generic chatbot or a fixed prompt chain.

The controlled task extracts estimated and allowable settlement measurements from
short fictional snippets into structured JSON. Each value is numeric or null when
absent, with supporting source evidence. These examples are anonymized/fictional
software fixtures, not professional engineering judgments. Twelve curated cases
cover decimals, nulls, allowable-only and estimated-only values, alternate wording,
zero, distractors, contradiction, unsupported units and embedded malicious text.
A second project has disjoint source and history for isolation checks.

The main fixture contains three actual local Git versions. v1 has risky rounding
and default-value instructions; v2 improves decimal handling while retaining a
missing-value risk; v3 improves null/evidence handling. These are hypotheses about
possible failures, not guaranteed model behavior. Observed live failures are
reported from saved responses. A separately labeled replay provider supplies
handwritten deterministic edge cases for reproducible control testing.

The principal design choices are one LangGraph coordinator, Gemini through the
google-genai SDK, SQLite domain memory, separate SQLite working checkpoints and a
CLI with a local Streamlit interface. A small schema and explicit operation ledger
make provenance and repeat behavior inspectable. A vector store, agent swarm,
automatic prompt rewriting, public deployment and uncontrolled Git writes were
excluded. These choices keep the prototype explainable for an individual viva.
The student must review these decisions and demonstrate understanding; AI-assisted
implementation is not proof of independent authorship or teacher approval.

The acceptance rules are versioned source knowledge. Initially the numeric
absolute tolerance is 0.01 mm; an explicitly approved correction changes it to
0.001 mm, retaining the superseded rules. A proposed correction remains pending
until a separate owner action. The agent may recommend a promotion candidate,
but only the developer records release approval. Approval of criteria, approval
of a prompt release, and teacher approval of the custom project are different.
Teacher approval remains unverified in the available records.

<div style="page-break-after: always;"></div>

## Page 2 — Agent loop, capabilities and controls

The controller identifies project, version, cycle key and approved policy, checks
prerequisites, then saves the immutable request and creates a review cycle. The
graph loads context, reads the registered Git blob/diff, retrieves bounded memory,
plans tests, validates the plan, executes selected tests, revalidates durable
outputs, reconciles failures, writes memory/audit and prepares a recommendation.
Conditional routing permits RUN_TESTS, REQUEST_CLARIFICATION or HOLD_FOR_APPROVAL.
Invalid plans fail closed to needs_review; no fixed test list replaces the LLM.

The planner receives current source, actual catalog, approved testing constraints
and historical failure/feedback records when enabled. It returns actual test IDs,
intent, a concise decision summary and evidence references. Its choice affects
which extraction calls execute. Python checks schema, ownership, allowed IDs,
required tests, budget and supplied references. The baseline budget allows four
tests including required T01, leaving three discretionary choices. Brief decision
summaries are stored; private chain-of-thought is not requested or retained.

Four meaningful capabilities are observable. The Git tool retrieves a real
registered SHA/blob/hash and diff through bounded read-only commands. The memory
tool retrieves project-scoped risks, outcomes, corrections and human feedback.
The executor makes actual Gemini extraction requests, distinct from planner calls,
and records responses, usage, latency and safe errors. The validator/store checks
outputs and commits durable results and audit events. These are different data
access, external execution and persistence capabilities, not inflated wrappers.

Validation is deterministic. Strict JSON parsing rejects duplicate keys, nonfinite
numbers, invalid shape and unsupported fields. Pydantic enforces contracts;
Decimal comparisons use approved tolerance. Null references cannot be replaced
by invented measurements. Evidence snippets must occur in the source. Contradictory
or unsupported-unit cases are uncertain. A model's confidence or self-evaluation
does not establish correctness.

Actual failures recommend revision. Errors, uncertainty, open risks and prior
human rejection prevent promotion. All selected tests passing with no unresolved
risk/rejection may produce a promotion candidate; this says nothing about untested
coverage. Human approval remains separate and additionally checks current policy,
completed cycle, matching version and no open risk. The UI calls these same backend
methods and performs no model work when simply rendering or refreshing.

Untrusted Git text, snippets, comments, memory and model outputs cannot introduce
tools, expand file paths, change policy or approve release. SDK retries and
continuation/function calling are disabled; the executor owns bounded attempts.
Recognized credentials are rejected/redacted at source, output, persistence and
export boundaries. Local actor labels are attribution, not authentication. The
UI is a loopback-only trusted-owner tool, not a publicly secured service.

<div style="page-break-after: always;"></div>

## Page 3 — Persistent memory and recovery

The authoritative domain database contains projects, immutable prompt versions,
versioned cases and policies, review cycles, planner decisions, tool operations,
operation attempts, extraction results, failure summaries, human decisions and
append-only audit events. Project IDs, UTC timestamps, canonical JSON/hash values
and source references link decisions to evidence. Composite foreign keys and
project-filtered queries prevent cross-project mixes, including guessed UUIDs.

Source knowledge comprises Git snapshots, cases and approved criteria. Long-term
task memory contains prior failures, resolutions/regressions, outcomes, human
feedback and approved corrections. Working memory contains the current graph
position, chosen IDs, pending work and result summaries in a separate SQLite
checkpointer. Re-reading source alone is not remembering a previous outcome, and
a graph checkpoint does not replace authoritative domain records.

Policy proposals stay pending. Separate explicit approval supersedes the old
policy atomically and activates the new revision. Historical cycles retain the
rules they used; new reviews use current approved criteria. Case changes add
revisions rather than rewriting old input/reference bodies. A failed case opens
a fingerprinted risk; a passing retest resolves it. Contradictory later evidence
reopens it as regressed. Earlier evidence remains in immutable audit events.
Untested risks do not disappear when unrelated tests pass.

Each logical extraction has a stable operation key and one unique durable result.
An operation can have multiple logged attempts without becoming multiple logical
actions. Repository mutations and their audit events commit together. Graph
re-entry reuses saved planning/results and skips identical memory writes even if
execution stopped between a committed result and the next checkpoint. An unknown
in-flight external request fails closed; remote exactly-once billing is not
promised. One worker per cycle is the supported concurrency model.

LangGraph uses SqliteSaver with a strict JsonPlusSerializer: dynamic-module
allowlists are empty and pickle fallback is disabled. Only trusted local
checkpoint files are supported. The saved request includes mode, source/base
identity, memory switch, model settings and replay fixture hash. A changed request
cannot reuse the same cycle key. Original domain/checkpoint/configuration must
be retained to resume; a terminal planner failure is not automatically resampled.

The original live run verified an actual process exit before the later v3 process.
The new process retrieved historical risk and reused original cases without
reseed/re-upload. Each completed review retained twelve checkpoints. Source IDs,
case hashes and the twelve main-case import events remained stable. The approved
tolerance correction was active in v3 while old rules remained queryable.

Archive is owner-controlled and retains inspectable history while blocking new
work. No deletion API or automatic expiry exists. Owners must manage runtime DBs,
checkpoints, backups and exports consistently for retention needs. Recognized-key
guards are not a universal secret detector or a promise of automatic legacy-data
erasure. These limits are part of the prototype's operating contract.

<div style="page-break-after: always;"></div>

## Page 4 — Evaluation and observed results

The original complete live v1 review selected T01,T02,T06,T07 and recommended
revision after decimal/quote failures. v2 selected T01,T02,T06,T05, retested earlier
issues and found a missing-limit failure. After process restart and approved
policy correction, v3 selected T01,T05,T07,T12; all four passed, the remaining risk
resolved and the recommendation became promotion candidate. Earlier v3 planner
deadline failures remain recorded rather than replaced by diagnostic responses.
The developer later explicitly approved that successful v3 cycle; no deployment
or Git promotion occurred.

Ten formal scenarios cover onboarding, later use, process restart, correction,
isolation, missing/conflicting evidence, tool retry, embedded untrusted instruction,
cross-version regression and remembered human rejection. All ten passed using
explicitly handwritten replay while real Git/SQLite/controller/graph/validator code
executed. This 10/10 is a control-scenario pass rate, not 100% live extraction
accuracy. Each result has observed state and evidence references in JSON/CSV.

Three controlled later-case pairs were defined before live comparison requests:
A01 after a decimal issue, A02 after a newly introduced missing-value issue, and
A03 after an approved correction and rejection. Each pair began from identical
SQLite copies with equal current prompt/diff, catalog/source IDs, approved policy,
model, temperature zero, seed null and budgets. Only long-term planner history
and its derived citation schema differed. Histories were scripted conditioning
fixtures; the six current review attempts used real Gemini. Exact requests,
schemas, settings, responses, selected/executed IDs and errors were preserved.

The predeclared combined selection/execution score was **1/3 with memory and
1/3 without memory**. A01 both arms selected/executed T02. A02 memory-on selected
historical T05 while memory-off did not, but quota errors prevented execution of
that selected case, so it did not meet the criterion. A03 memory-on's planner
failed with quota; no reasoning or HOLD decision is inferred. A03 memory-off ran
tests and needed review. Mandatory rejection protection remained active in both
arms and was deliberately not scored as a memory effect. Only one pair completed
without provider error. These three diagnostic pairs establish no statistical
advantage; provider limits confound conclusions about memory quality.

Five factual claims were audited against actual output/source/event evidence:
4.5 mm extraction, absent allowable value null, the registered v3 Git hash, the
human approval receipt and resolved risks with passing provenance. All five were
correct. Retry injection produced two extraction attempts and one completed logical
result; actual SQLite duplicate count was zero. The representative live A01
memory-on review used five calls and 6190 tokens, with 15.733 seconds summed
logical latency, 20.767 seconds wall time and 0.943 seconds local CPU. Process peak
RSS was 108308 KiB. Missing thinking-token counts and monetary cost remain unknown.

<div style="page-break-after: always;"></div>

## Page 5 — Reproduction, limitations and disclosure

The supported runtime is Python 3.14 on Linux, verified initially with Python
3.14.4 and SQLite 3.46.1. Direct dependencies and a complete development lock are
committed. The CLI can initialize and seed a fictional workspace, run a labeled
replay review without credentials, list/status/resume reviews, inspect memory,
approve a correction and record an explicit release decision. A local Streamlit
dashboard presents the same project-scoped data and backend actions. Initial
browsing/refresh never sends a model request. The README supplies the exact setup,
env template, launch commands and replay/live distinctions; final verification
records fresh-environment installation, regression checks, scenarios and demo.

The Module 10 regression suite passed 249 tests. Module 11's final test and clean
environment results are recorded separately in `artifacts/final/` and the status
document, avoiding invented future counts in this report. Automated UI tests
exercise actual widgets and verify backend side effects, read-only refresh and
explicit approval boundaries. Dependency API references and consulted official
documentation are linked in the architecture notes. No API key is required for
offline reproduction; live inference requires the user's configured account,
network and available quota, with data sent only on explicit review action.

Limitations include small curated fictional data, diagnostic rather than statistical
ablations, scripted conditioning histories, quota-limited live arms, nondeterminism
even at temperature zero, and partial test coverage on each recommendation. The
model alias can evolve at the provider; responses preserve reported metadata.
No superiority claim follows from these results. Larger repeated comparisons
under controlled provider capacity would be future evaluation, not an unreported
extension of the six-review experiment. No extra provider calls should be hidden
inside UI rendering, routine tests or a replay demonstration.

Operational limits are one worker per cycle, trusted local checkpoint files,
local actor attribution without multi-user authentication, bounded recognized-key
redaction and no automatic data-erasure mechanism. The application makes no
engineering safety determination or exactly-once remote billing promise. Teacher
approval of the custom idea, student review/understanding, and final report
pagination/submission remain actions for the student to verify; a working prototype
does not establish them. No repository push, public deployment or assignment
submission is authorized by the implementation work.

**AI assistance and external materials.** Codex assisted with planning, Python
implementation, tests, debugging, documentation and evaluation tooling. Reported
model outputs/metrics are from actual saved executions or explicitly labeled
replay; the distinction is retained in artifacts. The student must review, explain
and be able to modify submitted components, and complete authorship details.
No external dataset was imported: settlement snippets, expected answers, prompt
versions and replay cases are fictional project fixtures. External software is
used through pinned packages (Pydantic, Google GenAI/HTTPX, LangGraph and its
SQLite checkpointer, pytest, Streamlit and transitive dependencies). Those packages
retain their upstream licenses; this report does not claim they are student code.

Evidence index: [architecture](ARCHITECTURE.md), [memory schema](MEMORY_SCHEMA.md),
[scenario protocol](TEST_SCENARIOS.md), [measured evaluation](EVALUATION_RESULTS.md),
[nine-minute demo](DEMO_SCRIPT.md), [submission checklist](SUBMISSION_CHECKLIST.md),
[implementation/test status](IMPLEMENTATION_STATUS.md).
