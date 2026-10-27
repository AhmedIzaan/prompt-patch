"""Isolated Module 10 fixtures and evidence export, never production planning."""
import copy
import json
import sqlite3
from pathlib import Path

from promptpatch.git_tool import GitEvidenceTool, RepositoryAccess
from promptpatch.graph import ReviewGraph
from promptpatch.model_provider import ModelSettings, ProviderError, ProviderResponse
from promptpatch.repository import Repository, encode, utc_now
from promptpatch.security import reject_credentials
from promptpatch.tool_support import read_snapshot
from scripts.seed_demo import PROMPT_PATH, seed_demo

TABLES = ('projects', 'prompt_versions', 'test_cases', 'evaluation_policies',
          'review_cycles', 'planner_decisions', 'test_executions', 'failure_memories',
          'human_decisions', 'tool_operations', 'operation_attempts', 'audit_events')


def write(path, value):
    """Reject a sensitive artifact rather than alter source/hash evidence."""
    reject_credentials(value)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def fresh_directory(path):
    path = Path(path).resolve()
    if path.exists() and any(path.iterdir()):
        raise ValueError('Use a new empty output/runtime directory; existing evidence is preserved.')
    path.mkdir(parents=True, exist_ok=True)
    return path


def snapshot(db):
    with read_snapshot(db) as conn:
        return {table: [dict(row) for row in conn.execute(f'SELECT * FROM {table} ORDER BY rowid')]
                for table in TABLES}


def backup(source, destination):
    with sqlite3.connect(source) as left, sqlite3.connect(destination) as right:
        left.backup(right)


class Workspace:
    def __init__(self, root, *, seed=True):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db, self.checkpoint, self.repo = (self.root / name for name in
                                             ('domain.sqlite3', 'checkpoints.sqlite3', 'git'))
        if seed:
            seed_demo(self.db, self.repo, actor='module10-fictional-fixture-owner', approve_baseline=True)

    def versions(self, project='demo'):
        with read_snapshot(self.db) as conn:
            return {row['label']: dict(row) for row in conn.execute(
                'SELECT * FROM prompt_versions WHERE project_id=?', (project,))}

    def cases(self):
        with Repository(self.db) as store:
            return {row['case_key']: row for row in store.get_active_test_cases('demo')}

    def cycle(self, key, version='v3'):
        with Repository(self.db) as store:
            return store.create_review_cycle('demo', key, self.versions()[version]['id'])

    def graph(self, provider, settings=None):
        tool = GitEvidenceTool(self.db, {project: RepositoryAccess(self.repo, frozenset({PROMPT_PATH}))
                                        for project in ('demo', 'isolation')})
        return ReviewGraph(self.db, self.checkpoint, tool, provider,
                           settings or ModelSettings(model_id='module10-offline-replay'))

    def run(self, key, ids=None, *, version='v3', wrong=None, timeout_first=False):
        cycle = self.cycle(key, version)
        provider = FixtureProvider(self.cases(), ids or ['T01'], wrong=wrong, timeout_first=timeout_first)
        state = self.graph(provider).run('demo', cycle['id'])
        return state, provider


class FixtureProvider:
    """Handwritten replay: explicit choices supplied by test author, never LLM agency.

    This double has no memory_enabled argument or branch. Live ablations use
    GeminiProvider directly, not this double.
    """
    name, mode = 'replay', 'replay'

    def __init__(self, cases, ids, *, wrong=None, timeout_first=False):
        self.ids, self.wrong = ids, wrong or {}
        self.timeout_first, self.calls = timeout_first, []
        self.cases = {row['input_text']: row for row in cases.values()}

    def generate_once(self, prompt, input_text, settings, *, purpose, response_schema):
        self.calls.append({'purpose': purpose, 'input': input_text})
        if purpose == 'candidate_execution' and self.timeout_first:
            self.timeout_first = False
            raise ProviderError('timeout', retryable=True, timed_out=True, http_status=504)
        if purpose == 'planner':
            context = json.loads(input_text)
            value = {'decision': 'RUN_TESTS', 'test_ids': self.ids, 'test_mode': 'targeted_regression',
                     'reason_summary': 'Explicit handwritten fixture selection, not live inference.',
                     'memory_evidence_ids': [], 'source_evidence_refs': [context['source_refs'][0]],
                     'needs_developer_approval': False}
        else:
            case = self.cases[input_text]
            value = copy.deepcopy(json.loads(case['expected_json']))
            value.update(self.wrong.get(case['case_key'], {}))
        return ProviderResponse(provider='replay', mode='replay', purpose=purpose,
                                model_id=settings.model_id, raw_text=encode(value), elapsed_ms=0,
                                usage={}, finish_reason='REPLAY', fixture_id='module10-handwritten-fixture')


def evidence(workspace, states, **extra):
    return {'mode': 'offline-replay', 'live_inference': False, 'generated_at': utc_now(),
            'states': states, 'database_snapshot': snapshot(workspace.db), **extra}
