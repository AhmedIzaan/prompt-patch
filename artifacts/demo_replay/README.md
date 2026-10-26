# Module 08 handwritten replay demo

**Replay only.** Candidate outputs and test-selection plans are handwritten;
they are not captured Gemini responses or evidence of live LLM agency.

Three actual CLI worker processes and real SQLite/Git tools execute the fixture:

1. v1: T02 decimal and T03 missing-value failures; `revise`.
2. v2: T02 resolves, T03 remains open and T04 fails; `revise`.
3. New process, v3 under explicitly activated fixture policy revision 2:
   all four selected tests pass, the three risks resolve, `promote_candidate`.

Prompt release approval stays pending throughout. The policy approval actor and
reference explicitly say these are synthetic fixture actions, not the student's
release decision or teacher approval. No tokens or provider cost are invented.

`process_evidence.json` / `restart_evidence.txt` show the cycle 2 process exited
before cycle 3 started. Source hashes, case IDs and the 12 import events match
before and after, with no reseed after cycle 2. All requested artifacts are
present alongside raw planner/provider records and the scoped tool timeline.

This reproducible edge-case demonstration supplements `artifacts/demo/`, which
contains actual live behavior. It does not replace the live integration evidence.
