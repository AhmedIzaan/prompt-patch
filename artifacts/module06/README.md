# Module 06 live evidence

Fictional seeded cases only. Actual Gemini responses, not handwritten replay.
Model: `gemini-3.5-flash-lite`; SDK: `2.33.0`. Each successful graph executed
exactly its selected IDs. No human approval or release action was created.

| Artifact | Observed result |
|---|---|
| `initial.json` | v1 planner selected T01/T02/T06/T07; T02 and T06 failed numeric/quote validation; two risks persisted; recommendation `revise` |
| `memory_on.json` | First v2 attempt rejected because the guard required prefixed refs while Gemini cited actual supplied UUIDs; zero candidate calls |
| `memory_on_v2.json`, `memory_off_v2.json` | After accepting supplied UUIDs as well as refs, both selected T01/T02/T06/T07; four passes each; **no selection difference** |
| `v3_memory_on.json` | Planner selected T01/T02/T06/T07 but supplied catalog case refs as memory citations; rejected; zero candidate calls |
| `v3_memory_off.json` | Selected T01/T02/T11/T08; two passes and two uncertain results; `needs_review` |
| `v3_checked_memory_on.json` | Expanded per-field citation enums rejected by endpoint; `api_error`; zero candidate calls |
| `schema_probe.json` | One audited diagnostic request confirmed HTTP 400 / invalid argument; this is an error, not inference success |
| `v3_final_memory_on.json` | Reduced historical-citation schema accepted; selected T01/T02/T06/T07, cited the two original risks; four passes, risks resolved; `promote_candidate`, approval pending |
| `v3_final_memory_off.json` | Same current inputs/settings, historical evidence absent; selected T01/T02/T08/T11; two passes/two uncertain, T06 risk untested and still open; `needs_review` |
| `verification.json` | Matched current inputs/settings; selected IDs equal executed IDs; five model calls per final run, 12 checkpoints each; zero duplicate results; fresh-process repeats caused no new calls or writes; SQLite integrity/FK and credential checks passed |
| `comparison_definition.json` | Expectations recorded before diagnostic runs; subsequent schema repair rationale preserved |

The final pair started from fresh SQLite backups of the same post-v1 domain
state, with the same source/case/policy record identities. Planner context differs
only in `long_term_memory`. Model, temperature, token limit, retry limit and timeout
are equal. The response schema's historical-citation allowlist is mechanically
derived from the supplied memory; other fields and system instruction are equal.
The planner itself chose among all policy-allowed cases; Python did not substitute
a list based on the version or memory flag.

The final memory-enabled reason explicitly prioritizes the historical T02/T06
failures and cites their risk IDs. This is observable diagnostic evidence of
memory-sensitive selection, **not statistical proof**. Earlier identical and
rejected responses are retained. These checks do not constitute the three-case
Module 10 ablation, the Module 08 complete CLI/restart/correction demonstration,
or proof that untested extraction cases pass.

Runtime domain/checkpoint databases remain ignored under `data/module06/`;
exports are snapshots, not authoritative stores. The configured key was checked
for absence from these exports and isolated databases, without printing it.
Provider cost remains unknown (`null`). Telemetry for the final pair is in
`verification.json`; provider elapsed sums exclude graph/DB overhead.

Reproduce a single graph with the locally configured process environment:

```bash
python scripts/check_graph.py --version v3 --base-version v2 \
  --cycle-key unique-module06-check --output data/module06-check.json
```

Use separate equivalent SQLite backups and separate checkpoint paths when
comparing history modes. Reusing an existing cycle returns its original
checkpoint; changing its memory mode, base version or model settings is rejected.
