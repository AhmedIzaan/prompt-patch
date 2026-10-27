# Module 11 final verification

- **259/259 regression tests passed**, no skips, in a fresh isolated Python 3.14
  environment. One existing Google SDK Python deprecation warning remains.
- **10/10 UI widget tests passed**: read-only navigation, explicit setup,
  stable review key, replay execution/resume, approval confirmation, rejection
  protection, isolation/archive and safe opt-in environment parsing.
- **10/10 formal offline scenarios passed again**, with actual source/store/graph
  evidence in `scenarios/`.
- **Three-cycle replay demo passed**, including an actual subprocess restart,
  unchanged case imports and explicit synthetic policy correction. Outputs are
  replay, not new live model reasoning.
- Clean environment ran **11 CLI commands** from a different unused working
  directory, including real initialization/seeding/review/list/resume, without
  an API key, duplicate result or release decision.
- The local Streamlit HTTP page and health endpoint returned 200. Interactive
  behavior was verified with AppTest; no browser screenshot is claimed.
- Actual recorded live v3 renders as human-approved, without changing domain
  counts or making new provider calls.

See `verification.json`, `clean_environment.json`, `tests/`, `ui_http.json`,
`ui_recorded_demo.json`, `demo_replay/` and `scenarios/`. The initial UI check found
four failures caused by defaulting to the isolation project; the main demo default
was corrected and all final assertions passed. The repair is documented in
`ui_initial_check.json`.

Original Module 10 ablations remain **1/3 versus 1/3**, with two quota-limited
memory-on arms and only one error-free pair. They were not repeated or improved
by this final replay verification. No new live Gemini inference occurred.
Teacher approval, student authorship/review, actual report pagination if exported
and measured demo rehearsal remain student actions. No ZIP, PDF, push or submission
was requested/performed. Runtime databases and credentials are not committed.
