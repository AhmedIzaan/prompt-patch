# Memory and persistence

SQLite domain schema **1** is authoritative. `PROMPTPATCH_DB_PATH` identifies it;
`PROMPTPATCH_CHECKPOINT_DB_PATH` identifies a different trusted SQLite file used
by LangGraph. Initialize with `promptpatch init`; import the fictional baseline
with `promptpatch demo seed --actor developer --approve-baseline`. Both are
idempotent; initialization never reimports cases. Implementation:
[db.py](../src/promptpatch/db.py), [repository.py](../src/promptpatch/repository.py).

## Three distinct layers

| Layer | Content | Retrieval and lifetime |
|---|---|---|
| Source knowledge | Immutable Git SHA/blob/hash; approved case revisions; versioned policy | Read current registered source and approved criteria for each new review; historical sources retained |
| Long-term memory | Failures, resolution/regression events, meaningful outcomes, developer feedback and approved corrections | Bounded project-scoped retrieval across reviews/processes; hidden from the planner for memory-off comparisons |
| Working state | Selected IDs, pending node, result summaries, errors and source refs | Persisted LangGraph checkpoints for thread `project_id:cycle_id`; resume the same request |

A report/JSON export is a snapshot, not a database replacement. A checkpoint does
not replace a domain result or approval. Source knowledge alone is not evidence
that the agent remembered a prior decision.

## Domain tables and relationships

All child rows carry `project_id`. Scoped composite foreign keys enforce ownership
even if a caller guesses another project's UUID. IDs are UUIDs except the stable
owner-chosen project key. UTC timestamps use timezone-aware ISO strings.

| Table | Identity / important fields | Role and links |
|---|---|---|
| projects | id, name, created_at, archived_at | Local owner workspace and archive boundary |
| prompt_versions | project + label; git_commit_sha, prompt_path, content_hash, status | Immutable registered source; candidate/archived; human approval is separate |
| test_cases | project + case_key + revision; input_text, expected_json, tags_json, content_hash, active, supersedes_id | Versioned reference inputs; one active revision per key |
| evaluation_policies | project + revision; rules_json, status, supersedes_id, approved_at/by | pending → approved → superseded; at most one approved current revision |
| review_cycles | project + cycle_key; prompt_version_id, policy_id, status, completed_at | Pins source and policy; pending/running/completed/needs_review |
| planner_decisions | one per project + cycle; memory_enabled, decision_json, model_id | Exact instruction/context/schema/settings, raw response/error, selected IDs and supplied refs |
| tool_operations | project + operation_key; cycle_id, tool, request_hash, status, result_ref | Stable logical operation ledger; changed requests cannot reuse an operation |
| operation_attempts | operation_id, status, details_json, created_at | Individual completed/failed attempts, distinct from one logical action |
| test_executions | project + operation_key; cycle_id, test_case_id, response_json, validation_json, status, elapsed_ms | Immutable pass/fail/uncertain extraction result linked to approved policy and source |
| failure_memories | project + fingerprint; category, status, first/last_cycle_id, evidence_json, updated_at | Current open/resolved/regressed risk summary; earlier evidence in audit events |
| human_decisions | one per project + completed cycle; prompt_version_id, decision, comments, actor | Immutable explicit approved/rejected release decision |
| audit_events | event_type, ref_id, optional cycle_id, details_json, created_at | Append-only source/memory reads, writes, model calls, errors, transitions and owner actions |

`human_decisions.prompt_version_id` is the actual schema column. All version,
policy, case, operation and cycle references include project ownership. Queries
in tools/controllers and UI inventories also filter by project. The local owner
can enumerate project names/IDs; this is not a multi-user authorization system.

## Writes, corrections and consistency

Mutations and their audit events share `BEGIN IMMEDIATE` transactions. Connections
enable foreign keys and a bounded busy timeout. Initialization uses
`PRAGMA user_version`; concurrent initialization is tested. SQLite triggers prevent
updates/deletion of immutable source bodies, decisions, attempts, results and
audit history. Risk/current-policy/cycle status changes use controlled repository
methods and retain immutable provenance.

A policy proposal includes an actor and reason and stays pending. Separate owner
approval must name the current proposal. Approval atomically supersedes the old
policy and activates the new revision; stale proposals cannot replace a newer
approved one. Old rules remain queryable and completed cycles retain their pinned
policy. New reviews use the current approved policy. Resuming a partially executed
review after its policy was superseded fails closed; inspect it and start a new
review rather than mixing criteria. Case corrections similarly add a new revision
and deactivate the previous one, preserving hashes and old results.

A failed case creates a fingerprint `case:<case_uuid>`. Passing a tested case
resolves its risk. Contradictory later evidence reopens it as regressed, preserving
first/last cycle IDs and the audit sequence. Untested risks are never resolved
because other cases passed. Updating case revisions does not erase an old risk.

The graph recommends; `approvals.decide_version` enforces the explicit owner
boundary. Approval requires a completed promotion candidate under the current
policy and no open risks, with the exact version/cycle. Rejections are remembered
in future recommendations. One immutable human decision per cycle prevents
double approval. Local actor text records attribution, not authenticated identity.

## Restart, idempotency and bounds

LangGraph uses real `SqliteSaver` with `JsonPlusSerializer` configured with empty
dynamic-module allowlists and no pickle fallback. Only trusted locally created
checkpoint files may be opened. The immutable CLI request records provider mode,
model/settings, history switch, source/base IDs and replay fixture hash.

Completed planner/test operations are reused after restart. Each completed
extraction has one unique operation key, while retry attempts remain separate.
If a call may have reached the external service but no durable response exists,
the application does not blindly reissue it. This prevents avoidable duplicate
logical writes; it does **not** promise exactly-once provider billing. One worker
per cycle is supported. A failed planner is terminal for that cycle; checkpoint
resume is not a new inference attempt.

Memory retrieval defaults to ten rows per collection, with truncation flags and
128 KiB total bound. Catalog: at most 50 cases/64 KiB; prompt: 64 KiB; graph diff:
16 KiB. Fixture policy permits four tests with required T01 and three discretionary
slots. Planner: one attempt; extractions: default two attempts; request timeout
20 seconds by default, explicitly configurable up to 30 seconds.

## Retention, secrets and ownership

An explicit owner may archive a project through `Repository.archive_project`.
History stays inspectable through read-only status/list/timeline/UI snapshots;
new writes and audited tools/model work are blocked. No deletion API, automatic
expiry or silent history rewrite exists. An owner requiring erasure must stop all
processes and manage the domain/checkpoint files, backups and exports together;
this prototype does not implement selective deletion or compliance guarantees.

Runtime DBs, `.env`, keys and raw logs are ignored. Recognized credentials are
rejected at source/provider/persistence boundaries; logs/exports redact recognized
sensitive values. Legacy data is blocked rather than silently rewritten. This is
not universal arbitrary-secret detection. Back up both DB files after stopping
writers (or use SQLite's backup API); copying an active DB without its transaction
state is not the documented backup procedure.

Evidence: [Module 08 restart](../artifacts/demo/restart_evidence.txt),
[scenario rows](../artifacts/evaluation/scenarios.json),
[reliability controls](RELIABILITY_CONTROLS.md).
