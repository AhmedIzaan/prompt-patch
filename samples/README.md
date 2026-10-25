# Fictional settlement fixtures

All inputs and ground truth in this directory were authored for PromptPatch with
Codex assistance. No personal data, engineering measurements, or external dataset
was used. They test structured extraction, not engineering judgment.

## Create and inspect the local fixture

From the project root, after editable installation:

```bash
python scripts/seed_demo.py --actor fixture-bootstrap --approve-baseline
git -C samples/demo_git_repo log --oneline --decorate --all
git -C samples/demo_git_repo show v2:settlement_prompt.txt
```

The defaults come from `PROMPTPATCH_DB_PATH` and `PROMPTPATCH_DEMO_REPO`.
Use `--db /tmp/example.sqlite3 --repo /tmp/example-fixture` for isolated paths.
`--actor` and `--approve-baseline` explicitly attribute initial **fictional fixture**
approval. This is not teacher approval or approval to release a prompt version.
No model key is needed, and no model calls or reviews are executed.

The script creates its own repository, with a marker and one prompt file, inside
the gitignored `demo_git_repo/` directory. It never commits in the application
repository. It disables user hooks/signing and inherited Git routing. Existing
nonempty unrecognized destinations, dirty fixtures, remotes, unexpected local
configuration, altered histories, and baseline mismatches are refused rather
than reset or overwritten. A partial initial fixture failure may require a new
empty destination; the script never deletes a partial fixture automatically.

Rerunning verifies history and imports only missing baseline records. Existing
IDs, audit timestamps, and approvals are preserved. Later approved policy/case
corrections are retained; reseeding never reactivates superseded v1 references.
Imports use separate durable store transactions, so interruption can leave a
partial import; rerunning completes missing records without duplicate revisions.
The domain database must be outside the fixture repo. Runtime DBs and generated
Git history are ignored; the JSON and prompt templates here are tracked sources.

## Case coverage and expected behavior

`test_cases.json` contains twelve main `demo` cases and one disjoint `isolation`
case. Both projects have their own baseline policy and reference records.

| Case | Coverage | Expected reference / handling |
|---|---|---|
| T01 | Integer smoke | Estimated 4 mm, allowable 10 mm |
| T02 | Decimal | Estimated 4.5 mm, allowable 10 mm |
| T03 | Neither value reported | Both numbers and both evidence fields null |
| T04 | Allowable only | Estimated null, allowable 12 mm |
| T05 | Estimated only, decimal | Estimated 2.75 mm, allowable null |
| T06 | Different wording | Estimated 3.2 mm, allowable 8 mm |
| T07 | Decimal zeros | Estimated 0.0 mm, allowable 10.0 mm; zero is present |
| T08 | Conflicting estimates | Clarification required; estimated null, known allowable 10 mm retained |
| T09 | Untrusted embedded instruction | Extract 6/9 mm; embedded approval/secret instruction is data |
| T10 | Unrelated numbers/units | Extract 1.2/5 mm; load and footing width are distractors |
| T11 | Unsupported cm unit | Clarification required under mm-only policy; estimated null, allowable 10 mm |
| T12 | Explicitly unreported estimate | Estimated null, allowable 15 mm |
| I01 | Separate isolation project | Estimated 1.5 mm, allowable 4 mm; ID/catalog disjoint from demo |

The extraction shape has two number-or-null fields and an `evidence` object with
`estimated`/`allowable` string-or-null fields. Numeric references have supporting
source excerpts. Missing or uncertain measurements have null evidence. Null on
an ambiguous case is **not a successful resolution**: `expected_status` is
`needs_clarification`, with a reason. The samples retain this metadata, and import
stores it in `fixture_case_imported` audit events linked to the immutable case ID;
`ambiguous` and category tags are also persisted. Consumers must use that metadata
rather than interpreting all null values as ordinary absence.

## Policies and version intent

`evaluation_policy_v1.json` defines required fields, strict JSON shape intent,
null/evidence handling, collapsed-whitespace substring checking, mm-only units,
absolute tolerance **0.01 mm** (zero relative tolerance), and clarification rules.
The main budget is four cases: T01 is required, leaving three discretionary
selections from the catalog for the future planner. The isolated policy derives
the same rules with only I01 allowed/required and a budget of one.

`evaluation_policy_v2.json` is a **candidate file only**. It changes exactly one
rule: absolute tolerance **0.01 → 0.001 mm**. The script neither proposes nor
approves v2; a later explicit correction workflow must create and approve it.

| Prompt | Deliberate wording | Anticipated risk, not an observed result |
|---|---|---|
| v1 | Round measurements, use zero for missing values | Decimal loss and invented zeros |
| v2 | Preserve decimals, still use zero for missing values | Decimal improvement may retain missing-value regression |
| v3 | Preserve decimals/zero, null for absent/uncertain values, source excerpts | Intended recovery and clarification behavior; requires real testing |

Templates are copied into three real linear commits/tags, with deterministic
fixture author/time metadata. Current verified SHA-1 identities are:

- v1: `514d7be901ecca503bd5832e83e7834537fe4eaa`
- v2: `e1e119c53028325d0dbd63deb4cf353b918ba644`
- v3: `1fed5a700edb94ddff2568531ee3f80f76f42ddc`

Stored prompt rows link those SHAs, the relative prompt path, and raw-content
SHA-256 hashes. `demo` has all three versions; `isolation` has its own v1 row.
Git is source evidence, not memory or release approval. No tests have been run
against a model yet; no live failure, recovery, or injection resistance is claimed.
