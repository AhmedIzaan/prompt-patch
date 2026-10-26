# Module 08 live three-cycle demo — complete

Mode: **live Gemini**, requested/returned model `gemini-3.5-flash-lite`.
These are actual responses and SQLite/Git evidence, not replay.

| Cycle | Planner choices | Deterministic results | Recommendation |
|---|---|---|---|
| v1 | T01/T02/T06/T07 | pass/fail/fail/pass | revise |
| v2 | T01/T02/T06/T05 | pass/pass/pass/fail | revise |
| v3 | T01/T05/T07/T12 | pass/pass/pass/pass | promote_candidate |

The v2 planner cited both v1 failure risks, retested T02/T06 and selected T05
instead of T07; T05 exposed a missing-value regression. The restarted v3 planner
cited the saved T05 risk, retested it successfully and resolved it. **Prompt
release approval remains pending**; no human release decision was fabricated.
This is sequential evidence of memory-informed decisions, not controlled ablation
or statistical proof. Formal comparisons belong to Module 10.

The user explicitly approved tightening isolated demo tolerance **0.01 → 0.001
mm** in the conversation (“you have my approval”). The separate policy approval
is recorded with actor `developer` and the actual approval reference. Revision 2
was active during v3; revision 1 remains queryable as superseded. The earlier
`policy_correction_pending.json` is the preserved proposal snapshot, not current
approval state. Current evidence is `policy_correction.json`.

`restart_evidence.txt` and `process_evidence.json` record cycle-2 PID **161506**
exiting before successful v3 PID **180540** started. Original case IDs, Git/source
hashes and **12** import events match; no seed/upload occurred after v2. The same
persistent domain/checkpoint paths were used, and every completed review has
actual SQLite checkpoints. `verification.json` records direct DB read-back.

Failures and repairs are retained:

- The initial exporter conversion bug occurred after v1 had already persisted.
  The Module 08 runner was fixed and reused that result without another API call.
- The first v3 request and its explicit same-timeout retry failed before test
  execution: `cycle_3_attempt_1.json` and `cycle_3_attempt_2.json` retain them.
- Two standalone, audited diagnostic planner calls succeeded; their responses are
  in `schema_diagnostic.json` / `schema_original_order_diagnostic.json`. They do
  **not** count as completed workflow cycles or substitute for a graph decision.
- An observation-only CLI diagnostic captured **HTTP 504 / DEADLINE_EXCEEDED**:
  `cli_http_diagnostic.json` and `cycle_3_observed_failure.json`. No test ran in
  that failed diagnostic review.
- A small optional CLI timeout setting preserves the 20-second default. One
  explicit fresh attempt at the existing allowed maximum **30 seconds** completed
  successfully. Saved timeout/settings and all earlier failures remain auditable.

Thus the isolated DB contains **three completed reviews and three failed planner
reviews**, not three flawless attempts. The runner summary's two failed attempts
refer to its two managed attempts; the separately observed CLI failure is also
retained. There is no automatic fake fallback, hidden repeat-until-success loop,
source rewriting, or approval of a prompt release.

All required cycle, memory, correction, process, timeline and summary exports are
present. The owned runtime manifest and databases remain ignored under
`data/module08/live/`. Credential scans found no configured key in exports or
runtime files. Cost is unknown (`null`). Replay edge cases are separately labeled
under `artifacts/demo_replay/`; teacher approval remains unverified.
