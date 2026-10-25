"""Curated reference integrity and real, isolated Git fixture creation tests."""

from contextlib import closing
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest
from pydantic import ValidationError

from promptpatch.db import connect
from promptpatch.models import SettlementExtraction
from promptpatch.repository import Repository
from scripts.seed_demo import (
    FixtureError, PROMPT_PATH, SAMPLES, git, load_samples, seed_demo,
)


DATASET, POLICY, PROMPTS = load_samples()
SCRIPT = Path(__file__).resolve().parents[1] / "scripts/seed_demo.py"


def snapshot(db):
    with closing(connect(db)) as connection:
        names = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {name: [tuple(row) for row in connection.execute(f"SELECT * FROM {name} ORDER BY id")]
                for name in names}


@pytest.fixture
def seeded(tmp_path):
    db, repo = tmp_path / "memory.sqlite3", tmp_path / "fixture"
    result = seed_demo(db, repo, actor="offline-fixture-test", approve_baseline=True)
    return db, repo, result


@pytest.mark.parametrize("case", DATASET.cases + DATASET.isolation_cases, ids=lambda case: case.case_key)
def test_reference_schema_numbers_and_source_evidence(case):
    output = SettlementExtraction.model_validate(case.expected.model_dump())
    for field, quote in (("estimated_settlement_mm", output.evidence.estimated),
                         ("allowable_settlement_mm", output.evidence.allowable)):
        value = getattr(output, field)
        if value is None:
            assert quote is None
        else:
            assert quote and quote in case.input_text
            measurements = re.findall(r"(\d+(?:\.\d+)?)\s+mm", quote)
            assert Decimal(str(value)) in [Decimal(number) for number in measurements]
    assert bool(case.ambiguity_reason) == (case.expected_status == "needs_clarification")


def test_catalog_coverage_and_policy_budget():
    ids = [case.case_key for case in DATASET.cases + DATASET.isolation_cases]
    assert len(ids) == len(set(ids))
    assert len(DATASET.cases) == 12
    tags = {tag for case in DATASET.cases for tag in case.tags}
    assert {"decimal", "missing_value", "allowable_only", "estimated_only", "wording",
            "decimal_zero", "contradiction", "injection", "unit"} <= tags
    assert POLICY.rules["allowed_test_ids"] == [case.case_key for case in DATASET.cases]
    assert set(POLICY.rules["required_test_ids"]) <= set(POLICY.rules["allowed_test_ids"])
    assert POLICY.rules["max_tests_per_review"] - len(POLICY.rules["required_test_ids"]) >= 2
    assert next(case for case in DATASET.cases if case.case_key == "T08").expected_status == "needs_clarification"
    assert next(case for case in DATASET.cases if case.case_key == "T11").expected_status == "needs_clarification"


def test_candidate_policy_changes_exactly_one_criterion():
    candidate = json.loads((SAMPLES / "evaluation_policy_v2.json").read_text())
    changes = [key for key in POLICY.rules if POLICY.rules[key] != candidate["rules"][key]]
    assert set(POLICY.rules) == set(candidate["rules"])
    assert changes == ["numeric_absolute_tolerance_mm"]
    assert candidate["rules"][changes[0]] == 0.001
    assert candidate["status"] == "candidate_not_approved"


@pytest.mark.parametrize("bad", [True, "4.5", float("inf")])
def test_reference_contract_rejects_non_numeric_or_non_finite_values(bad):
    value = DATASET.cases[0].expected.model_dump()
    value["estimated_settlement_mm"] = bad
    with pytest.raises(ValidationError):
        SettlementExtraction.model_validate(value)


def test_seed_is_idempotent_with_actual_three_version_history(seeded):
    db, repo, result = seeded
    before = snapshot(db)
    second = seed_demo(db, repo, actor="offline-fixture-test", approve_baseline=True)
    assert second == result
    assert snapshot(db) == before
    assert len(set(result["prompt_shas"].values())) == 3
    assert len(git(repo, "rev-list", "--all").splitlines()) == 3
    assert git(repo, "status", "--porcelain") == b""
    assert result["model_calls"] == 0
    with closing(connect(db)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM review_cycles").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM test_executions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM human_decisions").fetchone()[0] == 0
        for project_id, count in (("demo", 12), ("isolation", 1)):
            assert connection.execute("SELECT COUNT(*) FROM test_cases WHERE project_id=?", (project_id,)).fetchone()[0] == count
            assert connection.execute("SELECT COUNT(*) FROM evaluation_policies WHERE project_id=?", (project_id,)).fetchone()[0] == 1
            assert connection.execute("SELECT status FROM evaluation_policies WHERE project_id=?", (project_id,)).fetchone()[0] == "approved"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_persisted_git_hashes_and_ambiguity_provenance_match_sources(seeded):
    db, repo, result = seeded
    with closing(connect(db)) as connection:
        prompts = connection.execute("SELECT * FROM prompt_versions WHERE project_id='demo'").fetchall()
        assert len(prompts) == 3
        for prompt in prompts:
            actual = git(repo, "show", f"{prompt['git_commit_sha']}:{prompt['prompt_path']}")
            assert actual == PROMPTS[prompt["label"]]
            assert hashlib.sha256(actual).hexdigest() == prompt["content_hash"]
        row = connection.execute("SELECT id FROM test_cases WHERE project_id='demo' AND case_key='T08'").fetchone()
        event = connection.execute(
            "SELECT details_json FROM audit_events WHERE project_id='demo' AND ref_id=? AND event_type='fixture_case_imported'",
            (row["id"],),
        ).fetchone()
        details = json.loads(event[0])
        assert details["fictional"] is True
        assert details["expected_status"] == "needs_clarification"
        assert details["source_ref"].endswith("#T08")


def test_seed_preserves_later_approved_corrections(seeded):
    db, repo, _ = seeded
    with Repository(db) as store:
        rules = json.loads(store.get_active_policy("demo")["rules_json"])
        rules["numeric_absolute_tolerance_mm"] = 0.002
        revised = store.propose_policy_revision("demo", rules, actor="test-owner", reason="Synthetic later correction")
        store.approve_policy_revision("demo", revised["id"], actor="test-owner")
        corrected_case = store.add_test_case_revision(
            "demo", "T01", "Synthetic corrected source", {"synthetic_correction": True}, ["synthetic"], actor="test-owner",
        )
    before = snapshot(db)
    seed_demo(db, repo, actor="offline-fixture-test", approve_baseline=True)
    assert snapshot(db) == before
    with Repository(db) as store:
        assert store.get_active_policy("demo")["id"] == revised["id"]
        assert corrected_case["id"] in {case["id"] for case in store.get_active_test_cases("demo")}


def test_parent_git_and_inherited_git_routing_are_untouched(tmp_path, monkeypatch):
    parent = tmp_path / "parent"
    parent.mkdir()
    git(parent, "init", "--quiet", "--initial-branch=main", "--template=")
    (parent / "sentinel.txt").write_text("existing parent work")
    (parent / ".gitignore").write_text("fixture/\n")
    git(parent, "add", "sentinel.txt", ".gitignore")
    git(parent, "commit", "--quiet", "-m", "Parent sentinel", date="2026-10-25T00:00:00+00:00")
    parent_head = git(parent, "rev-parse", "HEAD")
    parent_status = git(parent, "status", "--porcelain")
    monkeypatch.setenv("GIT_DIR", str(parent / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(parent))
    seed_demo(tmp_path / "db.sqlite3", parent / "fixture", actor="offline-fixture-test", approve_baseline=True)
    assert git(parent, "rev-parse", "HEAD") == parent_head
    assert git(parent, "status", "--porcelain") == parent_status
    assert (parent / "sentinel.txt").read_text() == "existing parent work"


def test_explicit_initial_fixture_approval_required_before_side_effects(tmp_path):
    with pytest.raises(FixtureError):
        seed_demo(tmp_path / "db.sqlite3", tmp_path / "repo", actor="test")
    assert list(tmp_path.iterdir()) == []


def test_unrecognized_destination_is_preserved(tmp_path):
    repo = tmp_path / "existing"
    repo.mkdir()
    (repo / "user-work.txt").write_text("preserve me")
    with pytest.raises(FixtureError):
        seed_demo(tmp_path / "db.sqlite3", repo, actor="test", approve_baseline=True)
    assert (repo / "user-work.txt").read_text() == "preserve me"
    assert not (tmp_path / "db.sqlite3").exists()
    assert not (repo / ".git").exists()


def test_git_metadata_destination_is_refused_before_side_effects(tmp_path):
    with pytest.raises(FixtureError):
        seed_demo(tmp_path / "db.sqlite3", tmp_path / ".git/fixture", actor="test", approve_baseline=True)
    assert list(tmp_path.iterdir()) == []


def test_duplicate_sample_ids_are_rejected_before_side_effects(tmp_path):
    copied = tmp_path / "samples"
    shutil.copytree(SAMPLES, copied, ignore=shutil.ignore_patterns("demo_git_repo"))
    path = copied / "test_cases.json"
    value = json.loads(path.read_text())
    value["cases"][1]["case_key"] = value["cases"][0]["case_key"]
    path.write_text(json.dumps(value))
    with pytest.raises(FixtureError):
        seed_demo(tmp_path / "db.sqlite3", tmp_path / "repo", actor="test", approve_baseline=True, sample_dir=copied)
    assert not (tmp_path / "db.sqlite3").exists()
    assert not (tmp_path / "repo").exists()


def test_dirty_fixture_is_not_overwritten(seeded):
    db, repo, _ = seeded
    before = snapshot(db)
    (repo / PROMPT_PATH).write_text("local user edit")
    with pytest.raises(FixtureError):
        seed_demo(db, repo, actor="test", approve_baseline=True)
    assert (repo / PROMPT_PATH).read_text() == "local user edit"
    assert snapshot(db) == before


def test_modified_baseline_source_refused_instead_of_reimported(seeded, tmp_path):
    db, repo, _ = seeded
    copied = tmp_path / "sample-copy"
    shutil.copytree(SAMPLES, copied, ignore=shutil.ignore_patterns("demo_git_repo"))
    path = copied / "test_cases.json"
    value = json.loads(path.read_text())
    value["cases"][0]["input_text"] = "Changed initial source"
    path.write_text(json.dumps(value))
    before = snapshot(db)
    with pytest.raises(FixtureError):
        seed_demo(db, repo, actor="test", approve_baseline=True, sample_dir=copied)
    assert snapshot(db) == before


def test_fresh_process_can_read_saved_cases_without_original_sources(seeded, tmp_path):
    db, _, _ = seeded
    result = subprocess.run([
        sys.executable, "-c",
        "import sys; from pathlib import Path; from promptpatch.repository import Repository; "
        "r=Repository(Path(sys.argv[1])); c=r.get_active_test_cases('demo'); "
        "print(len(c)); print(c[0]['case_key']); print(r.get_active_policy('demo')['revision']); r.close()",
        str(db),
    ], cwd=tmp_path, capture_output=True, text=True, check=True)
    assert result.stdout.splitlines() == ["12", "T01", "1"]


def test_script_cli_can_seed_and_reseed_in_separate_processes(tmp_path):
    db, repo = tmp_path / "db.sqlite3", tmp_path / "repo"
    args = [sys.executable, str(SCRIPT), "--db", str(db), "--repo", str(repo),
            "--actor", "offline-fixture-test", "--approve-baseline"]
    first = subprocess.run(args, cwd=tmp_path, capture_output=True, text=True, check=True)
    before = snapshot(db)
    second = subprocess.run(args, cwd=tmp_path, capture_output=True, text=True, check=True)
    assert json.loads(first.stdout) == json.loads(second.stdout)
    assert snapshot(db) == before
