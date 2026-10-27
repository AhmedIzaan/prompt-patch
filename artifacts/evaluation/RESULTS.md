# Module 10 evaluation results

Measured scenarios: **10/10** (100%), explicitly offline replay/control.
Live comparisons: **executed**. Memory-on **1/3**, memory-off **1/3**.
Pairs attempted: 3; completed without provider errors: 1. Provider-limited arms remain in the denominator as unsuccessful, not evidence of reasoning failure.
Conditioning histories are scripted. Diagnostic, not statistically significant.

| Comparison | Arm | Actual selected IDs | Planner action | Recommendation | Criterion met | Provider error |
|---|---|---|---|---|---|---|
| A01 | memory_on | T01, T02, T06, T07 | RUN_TESTS | promote_candidate | True | none |
| A01 | memory_off | T01, T02, T06, T07 | RUN_TESTS | promote_candidate | True | none |
| A02 | memory_off | T01, T02, T08, T11 | RUN_TESTS | needs_review | False | none |
| A02 | memory_on | T01, T05, T02, T04 | RUN_TESTS | needs_review | False | quota |
| A03 | memory_on | none | None | needs_review | False | quota |
| A03 | memory_off | T01, T02, T07, T11 | RUN_TESTS | needs_review | False | none |

Selection and execution are distinct. Each arm export lists executed IDs; a selected target blocked by a provider error does not meet the predeclared criterion. No planner response means no observed planner decision, even when the safe final action is needs_review.

Factual audit: **5/5** correct. Retry duplicate actions: **0**, measured from S07 SQLite.

Representative measurements: `representative_run.json`. Unknown token/cost values remain null. Local resource measurements are included.

Failures and limits:

- Ten scenarios measure controls with scripted provider, not live accuracy.
- Three pairs are diagnostic; no statistical or broad superiority claim.
- Conditioning history is scripted replay; current comparison model requests are live.
- Source/diffs may independently identify regressions even without history.
- Human rejection/open-risk enforcement remains active in both arms.
- Costs unknown; one worker/cycle; no exactly-once remote billing guarantee.
- Unmet ablation criteria: [{"comparison_id": "A02", "arm": "memory_off"}, {"comparison_id": "A02", "arm": "memory_on"}, {"comparison_id": "A03", "arm": "memory_on"}, {"comparison_id": "A03", "arm": "memory_off"}].
- Failed ablation requests: [{"comparison_id": "A02", "arm": "memory_on", "error": "quota"}, {"comparison_id": "A03", "arm": "memory_on", "error": "quota"}].
- Earlier v1 extraction failures and v3 deadline failure remain linked in `summary.json`.
- Teacher approval unverified. Actual v3 release approval saved separately in `release_approval.json`.

Evidence: [scenarios](scenarios.json), [CSV](scenarios.csv), [predeclared protocol](ablation/protocol.json), [five-claim audit](factual_claims.json).

See `docs/TEST_SCENARIOS.md` for commands. Exact requests/responses and source IDs remain in exports. No Module 11 report/submission package generated.
