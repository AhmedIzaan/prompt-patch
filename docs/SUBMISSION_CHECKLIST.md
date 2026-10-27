# Submission review checklist

Implementation artifacts are inspectable; this is not a claim that the student
has reviewed, submitted, or received teacher approval. No ZIP was requested, so
none is created. No push, upload, public deployment or assignment submission ran.

## Deliverables

- [x] Code, pinned direct dependencies and complete development lock.
- [x] README with CLI/UI setup, offline/live distinctions and restart commands.
- [x] Secret-free template at `config/.env.example`. The pre-existing local
  deletion of root `.env.example` is preserved; use the documented replacement.
- [x] Fictional cases, evaluation policies, versioned Git fixture seeder and
  schema/initialization; no external dataset required.
- [x] Architecture, memory lifecycle and documented controls/limitations.
- [x] Five-page-section technical report draft; export pagination still needs
  checking if a PDF is requested. No PDF submission is claimed.
- [x] Planned nine-minute demo script with restart, correction and failed cases.
- [x] Original live three-cycle/restart evidence, retained failures and separate
  actual v3 approval receipt.
- [x] Ten scenario JSON/CSV results, frozen ablation protocol and six attempted
  live arms; explicit quota limitations (only one error-free pair).
- [x] Five factual claims audit, retry SQL duplicates and representative resources.
- [x] Local Streamlit interface using existing backend services; clearly labeled
  replay, explicit model actions and separate release decisions.
- [x] Final automated checks retained in `artifacts/final/verification.json`: 259
  tests, clean environment, UI, three-cycle replay and all ten scenarios.
- [ ] Student inspect the evidence personally before submission; automated checks
  do not establish student review.

## Student actions before submission

- [ ] Obtain/record the teacher's actual decision about this custom project idea.
- [ ] Fill author/course/student identifiers into the technical report.
- [ ] Read and understand all implementation/AI-assisted changes; be able to modify
  and explain planner choice, deterministic guards, memory layers and retries.
- [ ] Review unsuccessful ablation criteria/provider errors and retain them in
  the report; do not label 10/10 offline controls as live accuracy or superiority.
- [ ] Rehearse the demo for 8–10 minutes and verify final report pagination if
  exported. A planned duration is not measured rehearsal evidence.
- [ ] Confirm final assignment instructions against the original PDF/course rules;
  that PDF was absent, so mapping uses the supplied master plan.
- [ ] Decide whether to submit a repository link or request a sanitized ZIP.
  Push commits personally as agreed; no automatic submission is configured.

## Secret and packaging boundary

If later packaging is explicitly requested, include tracked source, docs, safe
templates, fictional samples, dependency lock and sanitized evidence. Exclude
`.env`/`.env.*` credentials (retain only explicit templates), `.git`, `.venv`,
runtime `data/`, DB/checkpoint/WAL files, caches, raw logs, personal files and
machine-specific temporary wrappers. Do not archive by blindly recursing the
workspace. Inspect the actual manifest and scan actual configured keys before
sharing. Runtime DBs are not required to inspect committed evidence; regenerate
a separate replay workspace using documented commands.

The owner controls archive/retention; source/results/human history must not be
silently changed to sanitize a submission. Recognized-credential detection is
bounded. Local actor labels do not implement authentication, and opening the UI
to a public network is outside the verified deployment model.

## Assistance and external dependencies

Codex assisted with planning, implementation, tests, debugging, documentation and
evaluation tooling. The student owns review and the viva explanation. External
code consists of pinned upstream packages and standard-library tools; consult
their licenses. Fixture text/expected values/replays are fictional project data,
not a borrowed dataset. Actual Gemini responses are labeled live; handwritten
replay and SDK mocks are labeled separately. Teacher approval and student
understanding are never inferred from passing tests.
