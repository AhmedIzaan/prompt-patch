# PromptPatch requirement traceability

Updated 27 October 2026. Requirements come from the supplied master plan; the
assignment PDF was absent and has not been independently verified. Status below
distinguishes measured implementation from student/external actions.

| ID | Requirement | Current evidence and status |
|---|---|---|
| R01 | Useful recurring workflow | VERIFIED: versioned reviews and original live cycles in artifacts/demo; CLI/UI share controller |
| R02 | Three or more distinct capabilities including read/write | VERIFIED: Git evidence, historical retrieval, Gemini execution, deterministic validation and persistent SQLite result/audit |
| R03 | Observable evidence-dependent LLM decision | VERIFIED WITH LIMITS: real selected/executed IDs and risk citations; A02 paired selection differs but quota blocks target execution; no aggregate memory advantage claimed |
| R04 | Three cycles and process restart without reimport | VERIFIED: live process_evidence.json/restart_evidence.txt and stable source/case identities; final replay rerun separately labeled |
| R05 | Approved correction retained and used later | VERIFIED: actual tolerance 0.01→0.001 mm approval and v3 use; S04 same-output pass/fail difference; old policy retained |
| R06 | Distinct source, long-term memory and working checkpoints | VERIFIED: schema/store/checkpoint tests, MEMORY_SCHEMA.md; scoped UUIDs/FKs, timestamps, archive/history semantics |
| R07 | Interface with state, evidence and approval | VERIFIED: CLI list/status/logs/telemetry; Streamlit navigation/forms tests, read-only refresh, recorded v3 approval display and local HTTP check |
| R08 | Audits and retry safety | VERIFIED: operations/attempts/audit rows, S07 SQL duplicates 0, interruption/re-entry tests; no exactly-once remote billing claim |
| R09 | Real integration read and persistent write | VERIFIED: registered Git blobs, actual Gemini metadata and durable results; replay/mocks explicitly separate |
| R10 | Ten required scenarios | VERIFIED: 10/10 offline controls in artifacts/evaluation; final rerun in artifacts/final/scenarios; not live accuracy |
| R11 | Three predeclared memory pairs | MEASURED WITH LIMITS: six live attempts, identical paired snapshots, 1/3 vs 1/3; only one pair without provider errors; exact raw responses/errors and no significance claim |
| R12 | Five claims, duplicates and representative resources | VERIFIED: 5/5 claims; retry duplicates 0; actual calls/latency/tokens/CPU/RSS; cost unknown |
| R13 | Reproducibility, report and demo | IMPLEMENTED/TESTED with student checks remaining: lock/setup/template, final clean-env/demo/scenario/UI evidence, five-page-section report draft, nine-minute script, checklist; no ZIP requested |
| R14 | Assistance and external materials disclosure | DISCLOSED: README/report/checklist identify Codex, pinned packages and fictional fixtures. STUDENT ACTION: review, understand and demonstrate code; not inferred from tests |

Final actual test/installation results are in artifacts/final/verification.json
and [implementation status](IMPLEMENTATION_STATUS.md). Original live measurements
remain in [evaluation results](EVALUATION_RESULTS.md); final replay checks do not
replace or improve those outcomes.

The user approved successful v3 release in Module 10, separately from the earlier
tolerance correction. No Git source promotion, deployment, push or assignment
submission occurred. **Teacher approval remains unverified.** Student author
details, original course-rule checks, report pagination if exported and measured
demo rehearsal remain explicit submission tasks.
