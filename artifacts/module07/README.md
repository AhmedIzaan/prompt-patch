# Module 07 CLI evidence

- `live_cli.json`: actual subprocess commands for initialization, fictional
  baseline setup, a real Gemini v3 review, status, resume, memory and cycle logs.
  Gemini chose **T01/T02/T07/T11**, and exactly those cases executed. T01/T02/T07
  passed; T11 was uncertain (unsupported unit), so the recommendation was
  `needs_review`. Human approval stayed **pending**. Five actual model-call
  starts were recorded. A fresh-process status/resume returned identical output
  with unchanged domain table counts and no new model requests or writes.
- `replay_cli.json`: **handwritten replay**, not live inference. Thirteen CLI
  commands demonstrate separate synthetic owner approval, duplicate decision
  rejection, a pending policy proposal, explicit activation of revision 2,
  preservation of superseded revision 1, a subsequent review using revision 2,
  and resume/memory/log views. Human actions are simulated fixture actions,
  not the student's release decision or teacher approval.
- `verification.json`: post-run checks of the isolated databases/exports,
  SQLite integrity, foreign keys, duplicate completed results, source fixture
  history preservation, and credential absence. Counts are actual observations.

Runtime files are ignored under `data/module07/`; source Git is the already
verified fictional fixture. Exports are evidence snapshots, not authoritative
stores. The actual domain store and separate LangGraph checkpoints persist
request/decision/result/approval history. Credentials are never exported.

This is one live CLI check plus targeted offline workflow tests, **not** the
Module 08 complete three-version/restart/correction demonstration. Module 08
has not been implemented. The replay scenarios are available in
`samples/replay/module07_reviews.json`; see the repository README for commands.
