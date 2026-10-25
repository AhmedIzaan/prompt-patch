"""Create local fictional fixtures only; no provider calls or review outcomes.

Run from a checkout after editable installation. Git mutations are confined to
an empty destination or an already verified PromptPatch fixture repository.
"""

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError

from promptpatch.config import ConfigurationError, load_settings
from promptpatch.db import connect, initialize_database
from promptpatch.errors import StoreError
from promptpatch.models import SettlementExtraction
from promptpatch.repository import Repository, digest, encode


SAMPLES = Path(__file__).resolve().parents[1] / "samples"
PROMPT_PATH = "settlement_prompt.txt"
MARKER = '{"fixture_type":"promptpatch-fictional-demo","schema":1}\n'
PROJECT_NAMES = {"demo": "Fictional settlement demo", "isolation": "Fictional isolation fixture"}


class FixtureError(ValueError):
    """Existing data or destination cannot safely be seeded."""


class FixtureCase(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    case_key: str
    tags: list[str]
    input_text: str
    expected: SettlementExtraction
    expected_status: Literal["extractable", "needs_clarification"]
    ambiguity_reason: str | None


class FixtureDataset(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    dataset_id: str
    fictional: Literal[True]
    cases: list[FixtureCase]
    isolation_cases: list[FixtureCase]


class PolicyFile(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    revision: int
    status: str
    description: str
    rules: dict[str, JsonValue]


def load_samples(sample_dir=SAMPLES):
    dataset = FixtureDataset.model_validate_json((sample_dir / "test_cases.json").read_text())
    policy = PolicyFile.model_validate_json((sample_dir / "evaluation_policy_v1.json").read_text())
    all_cases = dataset.cases + dataset.isolation_cases
    keys = [case.case_key for case in all_cases]
    if not 8 <= len(dataset.cases) <= 12 or not dataset.isolation_cases or len(set(keys)) != len(keys):
        raise FixtureError("Fixture catalog size or unique case identities are invalid.")
    if policy.revision != 1 or policy.rules.get("allowed_test_ids") != [case.case_key for case in dataset.cases]:
        raise FixtureError("Initial policy does not match the main fixture catalog.")
    for case in all_cases:
        needs_clarification = case.expected_status == "needs_clarification"
        if needs_clarification != bool(case.ambiguity_reason) or needs_clarification != ("ambiguous" in case.tags):
            raise FixtureError("Ambiguity metadata is inconsistent.")
    prompts = {label: (sample_dir / "prompts" / f"{label}.txt").read_bytes()
               for label in ("v1", "v2", "v3")}
    return dataset, policy, prompts


def git(repo, *args, date=None):
    # Ignore inherited repository routing/config and user hooks/signing settings.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0", GIT_AUTHOR_NAME="PromptPatch Fixture",
               GIT_COMMITTER_NAME="PromptPatch Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
               GIT_COMMITTER_EMAIL="fixture@example.invalid")
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false",
         "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false",
         "-c", "tag.gpgsign=false", "-C", str(repo), *args],
        env=env, capture_output=True, timeout=15, check=False,
    )
    if result.returncode:
        raise FixtureError("Fixture Git operation failed; no parent repository changes were requested.")
    return result.stdout


def verify_git_fixture(repo, prompts):
    if not (repo / ".git").is_dir() or (repo / "FIXTURE.json").read_text() != MARKER:
        raise FixtureError("Destination is not a recognized fixture; existing files are preserved.")
    if Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve() != repo:
        raise FixtureError("Fixture must be its own Git repository.")
    config_keys = {entry.split(b"\n", 1)[0] for entry in
                   git(repo, "config", "--local", "--no-includes", "--null", "--list").split(b"\0") if entry}
    if config_keys - {b"core.repositoryformatversion", b"core.filemode", b"core.bare", b"core.logallrefupdates"}:
        raise FixtureError("Fixture has unexpected local Git configuration; refusing reuse.")
    if git(repo, "status", "--porcelain", "--untracked-files=all").strip() or git(repo, "remote").strip():
        raise FixtureError("Fixture has edits or remotes; refusing to modify it.")
    labels = set(git(repo, "tag", "--list").decode().splitlines())
    if labels != set(prompts):
        raise FixtureError("Fixture tags do not match v1/v2/v3.")
    shas = {label: git(repo, "rev-parse", f"refs/tags/{label}^{{commit}}").decode().strip()
            for label in prompts}
    if len(set(shas.values())) != 3 or len(git(repo, "rev-list", "--all").splitlines()) != 3:
        raise FixtureError("Fixture must have exactly three distinct commits.")
    previous = None
    for label, content in prompts.items():
        sha = shas[label]
        if git(repo, "show", f"{sha}:{PROMPT_PATH}") != content:
            raise FixtureError("Fixture prompt differs from tracked sample; no overwrite performed.")
        if git(repo, "show", f"{sha}:FIXTURE.json").decode() != MARKER:
            raise FixtureError("Fixture marker history is invalid.")
        if set(git(repo, "ls-tree", "-r", "--name-only", sha).decode().splitlines()) != {"FIXTURE.json", PROMPT_PATH}:
            raise FixtureError("Fixture commits must contain only the marker and prompt.")
        parents = git(repo, "rev-list", "--parents", "-n", "1", sha).decode().split()[1:]
        if parents != ([previous] if previous else []):
            raise FixtureError("Fixture versions must form a linear v1/v2/v3 history.")
        previous = sha
    if git(repo, "rev-parse", "HEAD").decode().strip() != shas["v3"]:
        raise FixtureError("Fixture HEAD must be v3; no checkout performed.")
    return shas


def ensure_git_fixture(repo, prompts):
    repo = Path(repo).resolve()
    if SAMPLES.resolve().is_relative_to(repo):
        raise FixtureError("Fixture destination must not contain the project source samples.")
    if repo.exists() and any(repo.iterdir()):
        return verify_git_fixture(repo, prompts)
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "--quiet", "--initial-branch=main", "--object-format=sha1", "--template=")
    (repo / "FIXTURE.json").write_text(MARKER)
    for index, (label, content) in enumerate(prompts.items()):
        (repo / PROMPT_PATH).write_bytes(content)
        git(repo, "add", "--", "FIXTURE.json", PROMPT_PATH)
        git(repo, "commit", "--quiet", "-m", f"Fictional settlement prompt {label}",
            date=f"2026-10-25T00:00:0{index}+00:00")
        git(repo, "tag", label)
    return verify_git_fixture(repo, prompts)


def project_rules(policy, project_id, cases):
    rules = dict(policy.rules)
    if project_id == "isolation":
        rules.update(allowed_test_ids=[case.case_key for case in cases],
                     required_test_ids=[cases[0].case_key], max_tests_per_review=1)
    return rules


def existing_row(reads, table, project_id, column, value):
    # Identifiers are internal constants; all variable values are bound and scoped.
    row = reads.execute(f"SELECT * FROM {table} WHERE project_id=? AND {column}=?",
                        (project_id, value)).fetchone()
    return dict(row) if row else None


def preflight_project(reads, project_id, cases, rules, prompts, shas, labels):
    project = reads.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if project and (project["name"] != PROJECT_NAMES[project_id] or project["archived_at"]):
        raise FixtureError("Existing project identity/state differs; no overwrite performed.")
    for label in labels:
        old = existing_row(reads, "prompt_versions", project_id, "label", label)
        if old and (old["git_commit_sha"] != shas[label] or old["prompt_path"] != PROMPT_PATH
                    or old["content_hash"] != hashlib.sha256(prompts[label]).hexdigest()):
            raise FixtureError("Stored prompt identity differs from this fixture.")
    old_policy = existing_row(reads, "evaluation_policies", project_id, "revision", 1)
    if old_policy and json.loads(old_policy["rules_json"]) != rules:
        raise FixtureError("Stored baseline policy differs; use explicit correction workflow.")
    for case in cases:
        old = reads.execute(
            "SELECT * FROM test_cases WHERE project_id=? AND case_key=? AND revision=1",
            (project_id, case.case_key),
        ).fetchone()
        expected = case.expected.model_dump()
        if old and old["content_hash"] != digest({"input": case.input_text, "expected": expected, "tags": case.tags}):
            raise FixtureError("Stored baseline reference differs; no silent reference correction allowed.")
        if old:
            event = reads.execute(
                "SELECT details_json FROM audit_events WHERE project_id=? AND ref_id=? AND event_type='fixture_case_imported'",
                (project_id, old["id"]),
            ).fetchone()
            if event:
                metadata = json.loads(event["details_json"])
                if (metadata["expected_status"] != case.expected_status
                        or metadata["ambiguity_reason"] != case.ambiguity_reason):
                    raise FixtureError("Stored ambiguity metadata differs; an explicit correction is required.")


def seed_demo(db_path, repo_path, *, actor, approve_baseline=False, sample_dir=SAMPLES):
    if not approve_baseline or not actor.strip():
        raise FixtureError("Explicit --approve-baseline and --actor are required for fictional initial references.")
    db_path, repo_path = Path(db_path).resolve(), Path(repo_path).resolve()
    if ".git" in db_path.parts or ".git" in repo_path.parts:
        raise FixtureError("Fixture files and databases must not be placed inside Git metadata.")
    if db_path.is_relative_to(repo_path):
        raise FixtureError("Keep the domain database outside the Git fixture.")
    dataset, policy, prompts = load_samples(Path(sample_dir))
    shas = ensure_git_fixture(repo_path, prompts)
    initialize_database(db_path)
    projects = {"demo": (dataset.cases, ("v1", "v2", "v3")),
                "isolation": (dataset.isolation_cases, ("v1",))}
    with Repository(db_path) as store, closing(connect(db_path)) as reads:
        # Verify all existing baseline content before adding any domain records.
        for project_id, (cases, labels) in projects.items():
            preflight_project(reads, project_id, cases, project_rules(policy, project_id, cases), prompts, shas, labels)
        for project_id, (cases, labels) in projects.items():
            if reads.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone() is None:
                store.create_project(project_id, PROJECT_NAMES[project_id])
            for label in labels:
                if existing_row(reads, "prompt_versions", project_id, "label", label) is None:
                    store.add_prompt_version(project_id, label, shas[label], PROMPT_PATH,
                                             hashlib.sha256(prompts[label]).hexdigest())
            baseline = existing_row(reads, "evaluation_policies", project_id, "revision", 1)
            if baseline is None:
                baseline = store.propose_policy_revision(
                    project_id, project_rules(policy, project_id, cases), actor=actor,
                    reason="Explicit fictional fixture baseline setup; not teacher or release approval.",
                )
            if baseline["status"] == "pending":
                store.approve_policy_revision(project_id, baseline["id"], actor=actor)
            for case in cases:
                row = reads.execute(
                    "SELECT * FROM test_cases WHERE project_id=? AND case_key=? AND revision=1",
                    (project_id, case.case_key),
                ).fetchone()
                if row is None:
                    row = store.add_test_case_revision(project_id, case.case_key, case.input_text,
                                                       case.expected.model_dump(), case.tags, actor=actor)
                imported = reads.execute(
                    "SELECT 1 FROM audit_events WHERE project_id=? AND ref_id=? AND event_type='fixture_case_imported'",
                    (project_id, row["id"]),
                ).fetchone()
                if imported is None:
                    store.append_audit_event(project_id, "fixture_case_imported", row["id"], {
                        "dataset_id": dataset.dataset_id, "fictional": True,
                        "expected_status": case.expected_status, "ambiguity_reason": case.ambiguity_reason,
                        "source_ref": f"samples/test_cases.json#{case.case_key}", "actor": actor,
                    })
    return {"fixture_only": True, "project_ids": list(projects), "prompt_shas": shas,
            "main_cases": len(dataset.cases), "isolation_cases": len(dataset.isolation_cases),
            "candidate_policy_v2": "file only; not imported or approved", "model_calls": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="Domain DB path; default from environment.")
    parser.add_argument("--repo", type=Path, help="Local fixture destination; default from environment.")
    parser.add_argument("--actor", required=True, help="Attribution for fictional baseline setup.")
    parser.add_argument("--approve-baseline", action="store_true", help="Explicitly approve fictional initial references only.")
    args = parser.parse_args(argv)
    try:
        settings = load_settings()
        db_path = args.db or settings.db_path
        if db_path.resolve() == settings.checkpoint_db_path.resolve():
            raise FixtureError("Domain and checkpoint databases must remain separate.")
        print(encode(seed_demo(db_path, args.repo or settings.demo_repo,
                               actor=args.actor, approve_baseline=args.approve_baseline)))
    except (ConfigurationError, FixtureError, StoreError, OSError, sqlite3.Error, ValidationError, subprocess.TimeoutExpired):
        print("Fixture setup failed. Check local configuration, destination ownership, and baseline consistency; existing files are not overwritten.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
