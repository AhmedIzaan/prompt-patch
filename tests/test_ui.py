"""Actual Streamlit widget tests; all execution is labeled offline replay."""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from promptpatch.config import load_settings
from promptpatch.repository import Repository
from promptpatch.reviews import Reviews
from promptpatch.tool_support import read_snapshot
from promptpatch.ui_launcher import launch_environment
from promptpatch.views import list_reviews, project_records
from scripts.seed_demo import seed_demo

APP = Path(__file__).resolve().parents[1]/'src/promptpatch/ui.py'
REPLAY = Path(__file__).resolve().parents[1]/'samples/replay/module07_reviews.json'


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    for name in ('GEMINI_API_KEY', 'GEMINI_MODEL', 'GOOGLE_API_KEY'):
        monkeypatch.delenv(name, raising=False)
    for name, value in {'PROMPTPATCH_MODE':'replay','PROMPTPATCH_DB_PATH':str(tmp_path/'domain.sqlite3'),
                        'PROMPTPATCH_CHECKPOINT_DB_PATH':str(tmp_path/'checkpoints.sqlite3'),
                        'PROMPTPATCH_DEMO_REPO':str(tmp_path/'git')}.items():
        monkeypatch.setenv(name, value)
    def forbidden(*args, **kwargs):
        raise AssertionError('UI test must never call live Gemini')
    monkeypatch.setattr('promptpatch.model_provider.GeminiProvider.generate_once', forbidden)
    return load_settings()


def element(elements, label):
    return next(e for e in elements if e.label==label)


def app():
    value = AppTest.from_file(APP, default_timeout=60).run()
    assert not value.exception, [e.message for e in value.exception]
    return value


def seeded(settings):
    seed_demo(settings.db_path, settings.demo_repo, actor='ui-offline-fixture-owner', approve_baseline=True)


def complete(settings, key='candidate'):
    return Reviews(settings).start('demo','v3',key,replay_file=REPLAY,replay_scenario='pass_v3')


def counts(settings):
    with read_snapshot(settings.db_path) as db:
        return {table:db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                for table in ('audit_events','review_cycles','planner_decisions','test_executions','human_decisions')}


def review_page(value):
    element(value.radio, 'Workspace').set_value('Reviews').run()
    assert not value.exception
    return value


def test_empty_ui_never_initializes_until_explicit_baseline_acceptance(workspace):
    a = app()
    assert not workspace.db_path.exists()
    element(a.button,'Initialize and load demo').click().run()
    assert a.error and not workspace.db_path.exists()
    element(a.checkbox,'I accept the fictional baseline evaluation criteria.').check()
    element(a.button,'Initialize and load demo').click().run()
    assert not a.exception
    assert len(project_records(workspace.db_path, 'demo')['versions'])==3
    assert counts(workspace)['review_cycles']==0


def test_browsing_pages_refresh_and_project_switch_are_read_only(workspace):
    seeded(workspace); complete(workspace)
    with Repository(workspace.db_path) as store:
        version=project_records(workspace.db_path,'demo')['versions'][0]
        cycle=store.create_review_cycle('demo','private-risk',version['id'])
        store.record_failure('demo',cycle['id'],'private-risk','PRIVATE_MAIN_MARKER',{'test_id':'T02'})
    before=counts(workspace)
    a=app()
    for page in ('Reviews','Memory & feedback','Policy','Overview'):
        element(a.radio,'Workspace').set_value(page).run()
        assert not a.exception
    element(a.button,'Refresh saved state').click().run()
    assert counts(workspace)==before
    element(a.selectbox,'Project').set_value('isolation').run()
    element(a.radio,'Workspace').set_value('Memory & feedback').run()
    assert not a.exception
    assert all('PRIVATE_MAIN_MARKER' not in str(frame.value) for frame in a.dataframe)
    assert any('No failure memories' in info.value for info in a.info)
    assert counts(workspace)==before


def test_replay_review_key_is_preserved_and_resume_does_not_repeat_work(workspace):
    seeded(workspace)
    a=review_page(app())
    element(a.text_input,'Review key').set_value('ui-first')
    element(a.button,'Run review').click().run()
    assert not a.exception, [e.message for e in a.exception]
    result=Reviews(workspace).status('demo','ui-first')
    assert result['mode']=='replay' and result['next_action']=='promote_candidate'
    assert result['approval']=='pending' and element(a.selectbox,'Saved review').value=='ui-first'
    before=counts(workspace)
    element(a.button,'Resume review').click().run()
    assert not a.exception and counts(workspace)==before
    element(a.button,'Refresh saved state').click().run()
    assert counts(workspace)==before


def test_release_requires_confirmation_then_uses_backend_approval(workspace):
    seeded(workspace); complete(workspace)
    a=review_page(app())
    element(a.button,'Record decision').click().run()
    with Repository(workspace.db_path) as store:
        assert not store.get_human_decisions('demo')
    element(a.checkbox,'I reviewed this exact version, results and evidence.').check()
    element(a.button,'Record decision').click().run()
    assert not a.exception
    result=Reviews(workspace).status('demo','candidate')
    assert result['approval']=='approved' and result['human_decision']['actor']=='developer'
    assert all(b.label!='Record decision' for b in a.button)
    before=counts(workspace)
    a.run()
    assert counts(workspace)==before and counts(workspace)['human_decisions']==1


def test_ui_rejection_is_retrieved_and_later_approval_guard_cannot_be_bypassed(workspace):
    seeded(workspace); complete(workspace)
    a=review_page(app())
    element(a.selectbox,'Decision').set_value('Reject release')
    element(a.text_area,'Decision notes').set_value('Needs developer follow-up <script>untrusted</script>')
    element(a.checkbox,'I reviewed this exact version, results and evidence.').check()
    element(a.button,'Record decision').click().run()
    assert not a.exception
    complete(workspace, 'after-rejection')
    a.run()
    element(a.selectbox,'Saved review').set_value('after-rejection').run()
    assert Reviews(workspace).status('demo','after-rejection')['recommendation']['prior_rejection']
    element(a.selectbox,'Decision').set_value('Approve release')
    element(a.checkbox,'I reviewed this exact version, results and evidence.').check()
    element(a.button,'Record decision').click().run()
    assert not a.exception and a.error
    with Repository(workspace.db_path) as store:
        assert [d['decision'] for d in store.get_human_decisions('demo')]==['rejected']


def test_live_render_and_unconfirmed_run_never_send_data(workspace, monkeypatch):
    seeded(workspace)
    monkeypatch.setenv('PROMPTPATCH_MODE','live')
    monkeypatch.setenv('GEMINI_API_KEY','test-ui-secret')
    monkeypatch.setenv('GEMINI_MODEL','test-ui-model')
    a=review_page(app())
    before=counts(workspace)
    element(a.button,'Run review').click().run()
    assert not a.exception and a.error and counts(workspace)==before
    assert 'test-ui-secret' not in str([t.value for t in a.text]+[t.value for t in a.markdown])


def test_archived_ui_retains_history_and_disables_mutations(workspace):
    seeded(workspace); complete(workspace)
    with Repository(workspace.db_path) as store:
        store.archive_project('demo',actor='ui-offline-owner')
    a=review_page(app())
    assert not a.exception and a.warning
    assert element(a.button,'Run review').disabled
    assert element(a.button,'Record decision').disabled
    assert element(a.button,'Resume review').disabled


def test_env_file_is_opt_in_data_with_environment_precedence(tmp_path):
    marker=tmp_path/'must-not-execute'
    env=tmp_path/'settings.env'
    env.write_text(f'GEMINI_API_KEY="test-file-secret"\nGEMINI_MODEL="$(touch {marker})"\nPROMPTPATCH_MODE=replay\nUNRECOGNIZED=value\n')
    result=launch_environment(env,{'GEMINI_API_KEY':'environment-wins'})
    assert result['GEMINI_API_KEY']=='environment-wins' and result['PROMPTPATCH_MODE']=='replay'
    assert result['GEMINI_MODEL']==f'$(touch {marker})' and not marker.exists()
    assert 'UNRECOGNIZED' not in result
    with pytest.raises(ValueError):
        launch_environment(None,{'PROMPTPATCH_DB_PATH':str(tmp_path/'same'),'PROMPTPATCH_CHECKPOINT_DB_PATH':str(tmp_path/'same')})


def test_env_file_cannot_echo_key_in_another_config_field(tmp_path):
    env=tmp_path/'wrong.env'
    env.write_text('GEMINI_API_KEY=opaque-test-secret\nGEMINI_MODEL=opaque-test-secret\n')
    with pytest.raises(ValueError) as caught:
        launch_environment(env,{})
    assert 'opaque-test-secret' not in str(caught.value)


def test_recent_review_inventory_is_scoped_read_only_and_latest_first(workspace):
    seeded(workspace); complete(workspace,'older'); complete(workspace,'newer')
    before=counts(workspace)
    result=list_reviews(workspace.db_path,'demo',1)
    assert [r['cycle'] for r in result['reviews']]==['newer']
    assert result['reviews'][0]['approval']=='pending'
    assert list_reviews(workspace.db_path,'isolation')['reviews']==[]
    with pytest.raises(ValueError):
        list_reviews(workspace.db_path,'demo',0)
    assert counts(workspace)==before
