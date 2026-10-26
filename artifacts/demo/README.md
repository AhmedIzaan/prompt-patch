# Module 08 live three-cycle demo

Mode: **live Gemini**, requested model `gemini-3.5-flash-lite`.
These are actual responses and SQLite/Git evidence, not replay.

- Cycle 1 (`cycle_1.json`): selected T01/T02/T06/T07. T02 and T06 failed numeric
  and supporting-quote checks, producing two persistent risks. Recommendation:
  `revise`; prompt release approval pending.
- Cycle 2 (`cycle_2.json`): explicitly cited both earlier risk records, retested
  T02/T06 successfully, and selected T05 in place of T07. T05 failed missing-value
  validation. Recommendation: `revise`; prompt release approval pending.
- `policy_correction_pending.json`: proposed tolerance change 0.01 → 0.001 mm.
  The existing policy remains active until a separate explicit owner approval.
- Cycle 3 and final restart/correction evidence are **pending owner approval**.

`memory_before_after.json` includes initial memory, memory after cycle 1 and the
state after the fully exited cycle 2. Runtime records and checkpoints remain in
ignored `data/module08/live/`. The runner's owned manifest records child PIDs,
start/exit times, outputs and CLI arguments. Original cases were seeded once.

The initial exporter had a SQLite-row conversion bug after the successful first
cycle. It was repaired in the Module 08 runner; rerunning reused that completed
cycle without another model call and recovered its export. No result or failure
was replaced with a fabricated success.

The live planner cited the original risks in cycle 2 and explained why it retested
them. The added T05 choice and resulting missing-value failure are observable.
This is sequential evidence, not a controlled memory ablation or statistical
causality claim; formal comparisons belong to Module 10.
