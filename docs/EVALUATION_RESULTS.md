# Evaluation results and interpretation

The authoritative measured Module 10 outputs are
[RESULTS.md](../artifacts/evaluation/RESULTS.md) and
[summary.json](../artifacts/evaluation/summary.json).
The [scenario protocol](TEST_SCENARIOS.md) explains exact rerun commands.

| Measure | Observed result | Meaning |
|---|---|---|
| Required behavior scenarios | 10/10 | Offline replay/control, real Git/SQLite/graph; not live accuracy |
| Memory comparisons | 1/3 on; 1/3 off | Predeclared combined selection/execution success; no demonstrated aggregate advantage |
| Pair completion | Three attempted; one without provider errors | A02 memory-on extraction and A03 memory-on planner were quota-limited |
| Factual claims sampled | 5/5 correct | Numeric value, absent null, Git source, human approval and risk state checked against sources/events |
| Retry duplicates | 0 | Actual SQLite count under S07 synthetic timeout/retry; not exactly-once billing |
| Representative live run | 5 calls, 6190 tokens, 15.733 s summed logical latency, 20.767 s wall, 0.943 s local CPU | A01 memory-on; process RSS 108308 KiB; no monetary estimate |

A01 both arms selected and executed T02. A02 memory-on selected historical T05;
memory-off did not. Only T01 executed in the memory-on arm before bounded quota
failure, so selection alone did not meet its criterion. A03 memory-on had no
planner response; no HOLD/clarification decision is inferred. Both quota-limited
arms remain unsuccessful in the three-case denominator, but these observations
cannot isolate a memory-quality effect. A03 memory-off ran tests and still needed
review under the authoritative rejection/uncertainty guards.

Histories in these paired snapshots are handwritten replay conditioning; current
comparison calls are real Gemini. Inputs/settings are equivalent except historical
retrieval and the derived history-citation schema. Exact instructions, prompts,
schema, settings, outputs and errors are preserved. Three pairs are diagnostic,
not statistically significant; even temperature zero is not a determinism claim.

The original Module 08 live workflow completed v1/v2/v3 with revise/revise/
promotion-candidate recommendations. It shows a genuine closed-process restart,
memory-informed selections, and the approved tolerance correction 0.01→0.001 mm.
Earlier failed planner/deadline attempts are retained. The user's later separate
v3 release approval is in
[release_approval.json](../artifacts/evaluation/release_approval.json); older exports
correctly show their historical pending state. Teacher approval is unverified.

Final Module 11 regression/clean-environment/UI/demo checks are recorded separately
under `artifacts/final/`; they do not overwrite these original live measurements
or silently resample the six previously authorized comparison reviews.
