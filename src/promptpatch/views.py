"""Read-only inventories for the CLI/UI; history stays project-scoped."""
import json

from promptpatch.repository import Repository
from promptpatch.security import redact
from promptpatch.tool_support import read_snapshot


def projects(db_path):
    # Local owner inventory only; no project history is returned here.
    with read_snapshot(db_path) as db:
        return redact([dict(r) for r in db.execute('SELECT id,name,created_at,archived_at FROM projects ORDER BY name,id')])


def project_records(db_path, project_id):
    with Repository(db_path) as store:
        project = store.get_project(project_id)
    with read_snapshot(db_path) as db:
        versions = [dict(r) for r in db.execute('SELECT * FROM prompt_versions WHERE project_id=? ORDER BY created_at,label', (project_id,))]
        policies = [dict(r) for r in db.execute('SELECT * FROM evaluation_policies WHERE project_id=? ORDER BY revision DESC', (project_id,))]
        risks = [dict(r) for r in db.execute('SELECT * FROM failure_memories WHERE project_id=? ORDER BY updated_at DESC', (project_id,))]
        feedback = [dict(r) for r in db.execute('SELECT * FROM human_decisions WHERE project_id=? ORDER BY created_at DESC', (project_id,))]
        events = [dict(r) for r in db.execute('SELECT * FROM audit_events WHERE project_id=? ORDER BY created_at DESC,rowid DESC LIMIT 200', (project_id,))]
    return redact({'project': project, 'versions': versions, 'policies': policies,
                   'risks': risks, 'human_decisions': feedback, 'events': events,
                   'timeline_limit': 200})


def list_reviews(db_path, project_id, limit=50):
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError('Invalid review listing limit.')
    with Repository(db_path) as store:
        store.get_project(project_id)
    with read_snapshot(db_path) as db:
        cycles = db.execute('''SELECT c.*,v.label AS version,h.decision AS approval,
            p.decision_json AS planner_json,
            (SELECT a.details_json FROM audit_events a WHERE a.project_id=c.project_id
             AND a.cycle_id=c.id AND a.event_type='graph_recommendation'
             ORDER BY a.created_at DESC LIMIT 1) AS recommendation_json
            FROM review_cycles c JOIN prompt_versions v ON v.project_id=c.project_id AND v.id=c.prompt_version_id
            LEFT JOIN human_decisions h ON h.project_id=c.project_id AND h.cycle_id=c.id
            LEFT JOIN planner_decisions p ON p.project_id=c.project_id AND p.cycle_id=c.id
            WHERE c.project_id=? ORDER BY c.created_at DESC,c.rowid DESC LIMIT ?''', (project_id, limit)).fetchall()
    results = []
    for row in cycles:
        planner = json.loads(row['planner_json']) if row['planner_json'] else {}
        recommendation = json.loads(row['recommendation_json']) if row['recommendation_json'] else {}
        results.append({'cycle_id': row['id'], 'cycle': row['cycle_key'], 'version': row['version'],
                        'status': row['status'], 'next_action': recommendation.get('action', 'resume_review'),
                        'approval': row['approval'] or 'pending', 'created_at': row['created_at'],
                        'mode': (planner.get('response') or {}).get('mode'), 'planner_error': planner.get('error')})
    return redact({'project_id': project_id, 'limit': limit, 'reviews': results})
