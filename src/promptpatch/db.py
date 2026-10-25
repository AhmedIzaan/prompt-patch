"""Versioned SQLite domain schema, separate from future LangGraph checkpoints."""

from pathlib import Path
import sqlite3

from promptpatch.errors import StoreError


SCHEMA_VERSION = 1

# Composite references include project_id even though UUID primary keys are global.
# This makes ownership a database invariant as well as a repository invariant.
SCHEMA = """
CREATE TABLE projects (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL,
    archived_at TEXT
);
CREATE TABLE prompt_versions (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
    label TEXT NOT NULL, git_commit_sha TEXT NOT NULL, prompt_path TEXT NOT NULL,
    content_hash TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'candidate'
        CHECK(status IN ('candidate','archived')),
    created_at TEXT NOT NULL, UNIQUE(project_id,label), UNIQUE(id,project_id)
);
CREATE TABLE test_cases (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
    case_key TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
    input_text TEXT NOT NULL, expected_json TEXT NOT NULL CHECK(json_valid(expected_json)),
    tags_json TEXT NOT NULL CHECK(json_valid(tags_json)), content_hash TEXT NOT NULL,
    active INTEGER NOT NULL CHECK(active IN (0,1)), supersedes_id TEXT,
    created_at TEXT NOT NULL, UNIQUE(project_id,case_key,revision), UNIQUE(id,project_id),
    FOREIGN KEY(supersedes_id,project_id) REFERENCES test_cases(id,project_id)
);
CREATE UNIQUE INDEX one_active_case ON test_cases(project_id,case_key) WHERE active=1;
CREATE TABLE evaluation_policies (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
    revision INTEGER NOT NULL CHECK(revision>0), rules_json TEXT NOT NULL CHECK(json_valid(rules_json)),
    status TEXT NOT NULL CHECK(status IN ('pending','approved','superseded')),
    supersedes_id TEXT, approved_at TEXT, approved_by TEXT, created_at TEXT NOT NULL,
    CHECK((status='pending' AND approved_at IS NULL AND approved_by IS NULL)
       OR (status IN ('approved','superseded') AND approved_at IS NOT NULL AND approved_by IS NOT NULL)),
    UNIQUE(project_id,revision), UNIQUE(id,project_id),
    FOREIGN KEY(supersedes_id,project_id) REFERENCES evaluation_policies(id,project_id)
);
CREATE UNIQUE INDEX one_approved_policy ON evaluation_policies(project_id) WHERE status='approved';
CREATE TABLE review_cycles (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
    cycle_key TEXT NOT NULL, prompt_version_id TEXT NOT NULL, policy_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','running','completed','needs_review')),
    created_at TEXT NOT NULL, completed_at TEXT,
    UNIQUE(project_id,cycle_key), UNIQUE(id,project_id),
    FOREIGN KEY(prompt_version_id,project_id) REFERENCES prompt_versions(id,project_id),
    FOREIGN KEY(policy_id,project_id) REFERENCES evaluation_policies(id,project_id)
);
CREATE TABLE planner_decisions (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), cycle_id TEXT NOT NULL,
    memory_enabled INTEGER NOT NULL CHECK(memory_enabled IN (0,1)),
    decision_json TEXT NOT NULL CHECK(json_valid(decision_json)), model_id TEXT NOT NULL,
    created_at TEXT NOT NULL, UNIQUE(id,project_id), UNIQUE(project_id,cycle_id),
    FOREIGN KEY(cycle_id,project_id) REFERENCES review_cycles(id,project_id)
);
CREATE TABLE tool_operations (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), cycle_id TEXT NOT NULL,
    operation_key TEXT NOT NULL, tool TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','completed','failed')),
    request_hash TEXT NOT NULL, result_ref TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    UNIQUE(project_id,operation_key), UNIQUE(id,project_id), UNIQUE(project_id,cycle_id,operation_key),
    FOREIGN KEY(cycle_id,project_id) REFERENCES review_cycles(id,project_id)
);
CREATE TABLE operation_attempts (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), operation_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('completed','failed')), details_json TEXT NOT NULL
        CHECK(json_valid(details_json)), created_at TEXT NOT NULL, UNIQUE(id,project_id),
    FOREIGN KEY(operation_id,project_id) REFERENCES tool_operations(id,project_id)
);
CREATE TABLE test_executions (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), cycle_id TEXT NOT NULL,
    test_case_id TEXT NOT NULL, operation_key TEXT NOT NULL, provider TEXT NOT NULL,
    model_id TEXT NOT NULL, response_json TEXT NOT NULL CHECK(json_valid(response_json)),
    validation_json TEXT NOT NULL CHECK(json_valid(validation_json)),
    status TEXT NOT NULL CHECK(status IN ('pass','fail','uncertain')),
    elapsed_ms REAL NOT NULL CHECK(elapsed_ms>=0), created_at TEXT NOT NULL,
    UNIQUE(project_id,operation_key), UNIQUE(id,project_id),
    FOREIGN KEY(cycle_id,project_id) REFERENCES review_cycles(id,project_id),
    FOREIGN KEY(test_case_id,project_id) REFERENCES test_cases(id,project_id),
    FOREIGN KEY(project_id,cycle_id,operation_key)
        REFERENCES tool_operations(project_id,cycle_id,operation_key)
);
CREATE TABLE failure_memories (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
    fingerprint TEXT NOT NULL, category TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('open','resolved','regressed')),
    first_cycle_id TEXT NOT NULL, last_cycle_id TEXT NOT NULL,
    evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json)), updated_at TEXT NOT NULL,
    UNIQUE(project_id,fingerprint), UNIQUE(id,project_id),
    FOREIGN KEY(first_cycle_id,project_id) REFERENCES review_cycles(id,project_id),
    FOREIGN KEY(last_cycle_id,project_id) REFERENCES review_cycles(id,project_id)
);
CREATE TABLE human_decisions (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
    prompt_version_id TEXT NOT NULL, cycle_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK(decision IN ('approved','rejected')),
    comments TEXT NOT NULL, actor TEXT NOT NULL CHECK(length(trim(actor))>0),
    created_at TEXT NOT NULL, UNIQUE(project_id,cycle_id), UNIQUE(id,project_id),
    FOREIGN KEY(prompt_version_id,project_id) REFERENCES prompt_versions(id,project_id),
    FOREIGN KEY(cycle_id,project_id) REFERENCES review_cycles(id,project_id)
);
CREATE TABLE audit_events (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), cycle_id TEXT,
    event_type TEXT NOT NULL, ref_id TEXT NOT NULL, details_json TEXT NOT NULL
        CHECK(json_valid(details_json)), created_at TEXT NOT NULL, UNIQUE(id,project_id),
    FOREIGN KEY(cycle_id,project_id) REFERENCES review_cycles(id,project_id)
);
CREATE INDEX risk_retrieval ON failure_memories(project_id,status,updated_at);
CREATE INDEX event_timeline ON audit_events(project_id,created_at);
CREATE INDEX execution_cycle ON test_executions(project_id,cycle_id);
"""


def _protections() -> str:
    statements = []
    for table in ("prompt_versions", "planner_decisions", "test_executions",
                  "human_decisions", "audit_events", "operation_attempts"):
        for action in ("UPDATE", "DELETE"):
            statements.append(
                f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'immutable record'); END;"
            )
    for table, columns in {
        "test_cases": "id,project_id,case_key,revision,input_text,expected_json,tags_json,content_hash,supersedes_id,created_at",
        "evaluation_policies": "id,project_id,revision,rules_json,supersedes_id,created_at",
        "review_cycles": "id,project_id,cycle_key,prompt_version_id,policy_id,created_at",
    }.items():
        statements.append(
            f"CREATE TRIGGER {table}_immutable_source BEFORE UPDATE OF {columns} ON {table} "
            "BEGIN SELECT RAISE(ABORT, 'immutable source'); END;"
        )
        statements.append(
            f"CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} "
            "BEGIN SELECT RAISE(ABORT, 'history retained'); END;"
        )
    return "\n".join(statements)


def connect(path: Path) -> sqlite3.Connection:
    """Open an existing domain store without accidentally creating a new one."""
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def initialize_database(path: Path) -> None:
    """Apply migration 1 atomically; repeated initialization preserves all data."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise StoreError("Database schema is newer than this application.")
        if version == 0:
            statement = ""
            for line in (SCHEMA + _protections()).splitlines(keepends=True):
                statement += line
                if sqlite3.complete_statement(statement):
                    connection.execute(statement)
                    statement = ""
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        connection.commit()
    finally:
        connection.close()
