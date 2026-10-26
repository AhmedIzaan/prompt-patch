# Module 09 evidence

This directory contains **targeted reliability/security checks**, not Module 10's
formal ten-scenario/three-ablation evaluation.

- `offline_tests.json` and `offline.junit.xml`: actual pytest return code,
  collected checks/failures/skips, stdout, elapsed time, measured child CPU and
  Linux peak RSS. Provider responses are handwritten replay or mocked SDK HTTP.
- `checks/*.json`: measured assertions and scoped SQLite evidence for retry,
  interruption, uncertainty, malicious input/Git content, forged actions/IDs,
  isolation, redaction, source/response/checkpoint credential guards, retention,
  repeated seed/approval and correction provenance. Test approvals are synthetic.
- `live_injection.json`: **one actual Gemini** v3/T09 extraction with additional
  malicious source instructions to disclose keys, alter policy, read a private
  path and approve a version. The input's legitimate 6/9 mm values were extracted
  and passed deterministic validation. Policy remained unchanged and human release
  decisions stayed zero. No private path or additional model tool was available.
  This single control is not evidence of universal model-injection resistance.
- `telemetry_live.json`: actual read-only CLI measurements for that saved cycle.
- `verification.json`: independent artifact/database, credential-absence, scope
  and duplicate checks after the final run.

The real provider returned `gemini-3.5-flash-lite`, SDK 2.33.0: **196 input + 58
output = 254 total tokens**, absent thinking-token count left unknown. Actual
provider time was **5910.855 ms**, logical execution **5982.826 ms**. Completed
operation reuse made **no second API call**; newer invocation wall time measures
reuse, not model generation. Cost is unknown/null. Runtime stores are ignored in
`data/module09/`; no credential or raw runtime database is committed.

Initial legacy-source fixture construction was rejected by the existing immutable
source trigger. The test was corrected to simulate an older writer with an added
revision, preserving the production invariant. No failing test was skipped or
acceptance weakened. The final tests include update paths and legacy checkpoints,
not just insert-time checks.

The controls do not authenticate local actors, erase old data, guarantee remote
exactly-once billing, or prove every possible unknown secret can be detected.
Source hashes/ground truth are not silently redacted; recognized sensitive source
material fails closed. See `docs/RELIABILITY_CONTROLS.md` for operating limits.
