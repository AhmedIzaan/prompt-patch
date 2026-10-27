# Nine-minute viva/demo

Use a terminal at the repository root and the local UI. Rehearse with replay and
saved live evidence to avoid depending on provider quota. Replay choices are
handwritten; explicitly say so. Do not call them fresh live intelligence. No real
release approval is needed for a demonstration. Do not overwrite the original
live evidence or use its recorded approval to approve a different review.

## Prepare before the timer

1. Install from the README in a clean environment. Set `PROMPTPATCH_MODE=replay`.
2. Start with new paths: `PROMPTPATCH_DB_PATH=data/viva/domain.sqlite3`,
   `PROMPTPATCH_CHECKPOINT_DB_PATH=data/viva/checkpoints.sqlite3`,
   `PROMPTPATCH_DEMO_REPO=data/viva/git`. Use an unused `data/viva` directory.
3. Launch the UI with `python scripts/run_ui.py` and keep the terminal available.
   Opening the UI does not initialize, seed or call the model automatically.
4. Keep `artifacts/demo/`, `artifacts/evaluation/RESULTS.md` and the five-page
   technical report available. Saved evidence works without runtime DBs/API keys.

## 0:00–1:00 — Problem and onboarding

Explain forgotten regressions across prompt updates, fictional settlement values,
and the separation between recommendation and human release approval. Use the
UI's explicit setup action or:

```bash
promptpatch init
promptpatch demo seed --actor viva-owner --approve-baseline
```

Show two projects, twelve main cases, three registered Git versions and approved
policy 1. Say that the fixture owner approves fictional baseline criteria here.

## 1:00–2:00 — First cycle

```bash
promptpatch review start --project demo --version v1 --cycle viva-c1 \
  --replay-file samples/replay/module08_cycles.json --replay-scenario cycle_1
promptpatch review list --project demo
promptpatch review status --project demo --cycle viva-c1
```

Inspect selected/executed IDs, failed decimal, raw source refs, new risk and revise
recommendation. UI Reviews shows the same persisted cycle. Explain what the LLM
would choose in live mode versus what Python validates; this command is replay.

## 2:00–3:00 — Later cycle and evidence-dependent live decisions

```bash
promptpatch review start --project demo --version v2 --base-version v1 --cycle viva-c2 \
  --replay-file samples/replay/module08_cycles.json --replay-scenario cycle_2
promptpatch memory show --project demo
```

Show earlier failure retrieved/retested and a new missing-value regression.
Then show original real `artifacts/demo/cycle_1.json` and `cycle_2.json`: actual
Gemini choices were T01,T02,T06,T07 then T01,T02,T06,T05. Distinguish actual saved
live agency from scripted demo routing. Git diff is source evidence, not memory.

## 3:00–4:30 — Explicit correction and actual process restart

```bash
promptpatch policy propose --project demo --file samples/evaluation_policy_v2.json \
  --actor viva-owner --reason "Demonstration: tighten numerical tolerance"
promptpatch policy approve --project demo --revision 2 --actor viva-owner
```

Show pending before approval, then old superseded policy and active revision 2.
These two CLI invocations are separate owner actions. Close the running UI with
Ctrl+C and confirm exit; the earlier CLI workers already exited too. Launch it
again using the same env paths, with no seed/import command. Start:

```bash
promptpatch review start --project demo --version v3 --base-version v2 --cycle viva-c3 \
  --replay-file samples/replay/module08_cycles.json --replay-scenario cycle_3
```

Inspect saved cases, prior risk, revision 2 and promotion candidate. Show original
live `restart_evidence.txt`/`process_evidence.json` for recorded PIDs/exit order and
unchanged imports. Explain checkpoint versus source versus long-term task memory.

## 4:30–5:30 — Human boundary and repeat safety

View the release form without submitting a real approval. Explain backend guards
and immutable human rows. Show the actual separate v3 approval receipt from the
user's Module 10 decision. Historical live exports still show then-pending state.

```bash
promptpatch review resume --project demo --cycle viva-c3
promptpatch telemetry show --project demo --cycle viva-c3
```

No new logical result or model call should appear after completed resume. Use
S10 evidence for synthetic rejection remembered in a later passing review.

## 5:30–6:30 — Negative cases and isolation

Show `artifacts/evaluation/evidence/S06.json`: null missing values and uncertain
contradiction/unit cases. Show S07's failed attempt, successful retry and SQL
duplicates zero. Show S08's malicious sentence, unchanged policy/approval and
outside-path denial. Switch UI project to isolation: no main-project risks or
decisions appear. Explain that this is local owner project isolation, not login.

## 6:30–7:45 — Formal evaluation and limitations

Show 10/10 offline scenarios, five checked facts and the actual six-arm ablation
table. Explain frozen protocol, identical paired snapshots, scripted conditioning,
live current calls, 1/3 versus 1/3, A02 selection change but quota-blocked execution,
and A03 missing planner response. Only one pair completed without provider errors.
Do not claim statistical superiority or hide those failed criteria.

Show representative five calls, 6190 tokens and actual latency/resources. Cost
and absent thinking tokens are unknown, not zero. Point out earlier retained v3
deadline failures and that a failed planner is not automatically resampled.

## 7:45–9:00 — Code and student explanation

Open planner/graph/evaluator/repository/approvals. Explain one full trace from Git
source → historical risk → actual selection → extraction → deterministic result →
memory write → human decision. Name three different capabilities and why their
permissions differ. Show dependency lock, clean-environment verification, final
tests and secret-free template. Disclose Codex assistance and identify code/design
decisions you reviewed or changed. State teacher approval accurately.

Expected viva questions: Why does source re-reading not prove memory? What changes
when history is hidden? How is a timeout different from an extraction failure?
Which action is idempotent? Why is promotion only a candidate? What cannot be
concluded from quota-limited ablations? What is still unverified by the student?

Nine minutes is a planned schedule; no measured rehearsal duration is claimed.
