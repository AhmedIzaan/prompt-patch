"""Local Streamlit workspace. Rendering reads; only explicit forms perform work."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from uuid import uuid4

import streamlit as st

from promptpatch.approvals import decide_version
from promptpatch.config import load_settings
from promptpatch.db import initialize_database
from promptpatch.errors import StoreError
from promptpatch.model_provider import ProviderError
from promptpatch.reviews import Reviews, ReviewError
from promptpatch.security import redact, redact_text, reject_credentials
from promptpatch.telemetry import review_telemetry
from promptpatch.tool_support import ToolError
from promptpatch.views import projects, project_records, list_reviews

ROOT = Path(__file__).resolve().parents[2]
REPLAY = ROOT/'samples/replay/module07_reviews.json'
STYLE = '''<style>
.block-container {max-width: 1220px; padding-top: 2.4rem; padding-bottom: 3rem;}
h1 {letter-spacing: -.055em; font-weight: 750;}
h2,h3 {letter-spacing: -.025em;}
[data-testid="stMetric"] {background: white; border: 1px solid #e2e9ed; border-radius: 12px; padding: 16px 20px;}
[data-testid="stSidebar"] {border-right: 1px solid #e2e9ed;}
[data-testid="stCaptionContainer"] {color: #5e7380;}
.stButton > button, .stFormSubmitButton > button {border-radius: 8px;}
</style>'''


def perform(action):
    """Never show raw SDK/configuration exceptions in the browser."""
    try:
        value = action()
        return redact(value) if isinstance(value, (dict, list)) else value
    except ProviderError as exc:
        st.error('Provider unavailable ('+exc.code+'). No successful result or approval is inferred.')
    except (StoreError, ToolError, ReviewError) as exc:
        st.error(redact_text(str(exc)))
    except (ValueError, OSError, sqlite3.Error, subprocess.SubprocessError):
        st.error('Action could not complete. Check configuration and source files; inspect the saved review errors. No approval was inferred.')
    return None


def ui_settings():
    settings = load_settings()
    reject_credentials(settings.model_dump())
    if settings.db_path.resolve() == settings.checkpoint_db_path.resolve():
        raise ReviewError('Domain and checkpoint files must differ.')
    return settings


def bootstrap(settings, actor):
    if not actor.strip() or len(actor) > 128:
        raise ValueError('Invalid actor.')
    if settings.db_path.resolve() == settings.checkpoint_db_path.resolve():
        raise ValueError('Domain and checkpoints must differ.')
    initialize_database(settings.db_path)
    script = ROOT/'scripts/seed_demo.py'
    if not script.is_file():
        raise ReviewError('Use the editable checkout to load the fictional demo.')
    result = subprocess.run([sys.executable, str(script), '--db', str(settings.db_path.resolve()),
                             '--repo', str(settings.demo_repo.resolve()), '--actor', actor, '--approve-baseline'],
                            capture_output=True, text=True, check=False, timeout=60)
    if result.returncode:
        raise ReviewError('Fixture setup failed. Check destination ownership and baseline consistency.')
    return {'ready': True}


def setup(settings):
    st.title('Your review workspace')
    st.write('Load fictional prompt versions, reference cases and baseline criteria to start your first review.')
    with st.form('setup'):
        actor = st.text_input('Developer name', value='developer', max_chars=128)
        accepted = st.checkbox('I accept the fictional baseline evaluation criteria.')
        submitted = st.form_submit_button('Initialize and load demo', type='primary')
    if submitted:
        if not accepted:
            st.error('Accept the displayed baseline scope before loading it.')
        else:
            with st.spinner('Preparing local fixtures…'):
                if perform(lambda: bootstrap(settings, actor)):
                    st.rerun()
    with st.expander('Baseline criteria'):
        policy = ROOT/'samples/evaluation_policy_v1.json'
        if policy.is_file():
            st.json(redact(json.loads(policy.read_text())))
        st.caption('Twelve fictional main cases, three Git prompt versions and one isolated test project. No provider request is made.')


def overview(data, reviews):
    st.title('A clearer view of every change')
    st.write('Review prompt versions, revisit past failures, and keep release decisions grounded in evidence.')
    active = next((p for p in data['policies'] if p['status']=='approved'), None)
    cols = st.columns(4)
    cols[0].metric('Prompt versions', len(data['versions']))
    cols[1].metric('Recent reviews', len(reviews))
    cols[2].metric('Open risks', sum(r['status'] in {'open', 'regressed'} for r in data['risks']))
    cols[3].metric('Active policy', 'Revision '+str(active['revision']) if active else 'Not approved')
    st.subheader('Recent reviews')
    if reviews:
        st.dataframe([{k: r[k] for k in ('cycle','version','status','next_action','approval','created_at')} for r in reviews],
                     hide_index=True, width='stretch')
        st.caption('Choose Reviews in the sidebar to inspect evidence or start a new run. Recommendations and human decisions remain separate.')
    else:
        st.info('No reviews yet. Open Reviews to test your first prompt version.')
    st.subheader('Version history')
    st.dataframe([{'Version': v['label'], 'Git revision': v['git_commit_sha'][:12],
                   'Source': v['prompt_path'], 'Registered': v['created_at']} for v in data['versions']],
                 hide_index=True, width='stretch')


def start_review(settings, project, data, scope):
    with st.expander('Start a new review', expanded=not list_reviews(settings.db_path, project)['reviews']):
        versions = [v['label'] for v in data['versions'] if v['status']=='candidate']
        if not versions:
            st.info('No active prompt versions available.')
            return
        with st.form('start-'+scope):
            left, right = st.columns(2)
            version = left.selectbox('Prompt version', versions, index=len(versions)-1)
            base = right.selectbox('Compare with', ['None']+versions)
            draft_key = 'draft-key-'+scope
            if draft_key not in st.session_state:
                st.session_state[draft_key] = 'review-'+uuid4().hex[:8]
            key = st.text_input('Review key', key=draft_key, max_chars=128,
                                help='A stable identifier. Reusing an identical request resumes saved work.')
            memory = st.checkbox('Use saved failure history and developer feedback', value=True)
            if settings.mode=='replay':
                st.caption('OFFLINE REPLAY · Handwritten fixture choices and answers. No external model calls.')
                fixture = st.selectbox('Replay scenario', ['pass_v3','fail_v3','decimal_pass_v3','hold_v3','retry_v3'])
                allowed = True
            else:
                fixture = None
                st.caption('LIVE GEMINI · Uses the configured model and available account quota.')
                allowed = st.checkbox('Send this review’s prompt, cases, policy and relevant history to Google Gemini.')
            run = st.form_submit_button('Run review', type='primary', disabled=bool(data['project']['archived_at']))
        if run:
            if not allowed:
                st.error('Confirm the live data submission before running this review.')
            elif not key.strip():
                st.error('Enter a review key.')
            else:
                with st.spinner('Review running. Selected tests and outcomes will be saved…'):
                    result = perform(lambda: Reviews(settings).start(project, version, key,
                        base_label=None if base=='None' else base, memory_enabled=memory, timeout_ms=30000,
                        replay_file=REPLAY if fixture else None, replay_scenario=fixture))
                if result:
                    st.session_state['jump_to_cycle'] = (scope, key)
                    st.rerun()


def release_form(settings, project, status, scope, archived):
    st.subheader('Developer decision')
    if status['human_decision']:
        decision = status['human_decision']
        st.success('Recorded decision: '+decision['decision'])
        st.caption('By '+decision['actor']+' · '+decision['created_at'])
        st.text(decision['comments'] or 'No comment supplied.')
        return
    st.caption('A promotion candidate is a recommendation. Your decision is saved separately for this exact review.')
    with st.form('release-'+scope+'-'+status['cycle_id']):
        decision = st.selectbox('Decision', ['Approve release', 'Reject release'])
        actor = st.text_input('Decision by', value='developer', max_chars=128)
        comments = st.text_area('Decision notes', max_chars=2000)
        confirmed = st.checkbox('I reviewed this exact version, results and evidence.')
        submitted = st.form_submit_button('Record decision', disabled=status['status']!='completed' or archived)
    if submitted:
        if not confirmed:
            st.error('Review and confirm the evidence before recording a decision.')
        else:
            result = perform(lambda: decide_version(settings.db_path, project, status['version'], status['cycle'],
                             'approved' if decision=='Approve release' else 'rejected', actor=actor, comments=comments))
            if result:
                st.rerun()


def reviews_page(settings, project, data, reviews, scope):
    st.title('Prompt reviews')
    st.write('See what ran, why it was selected, and what needs your decision.')
    start_review(settings, project, data, scope)
    if not reviews:
        return
    keys = [r['cycle'] for r in reviews]
    widget = 'cycle-'+scope
    jump = st.session_state.get('jump_to_cycle')
    if jump and jump[0]==scope and jump[1] in keys:
        st.session_state[widget] = jump[1]
        del st.session_state['jump_to_cycle']
    key = st.selectbox('Saved review', keys, key=widget)
    status = perform(lambda: Reviews(settings).status(project, key))
    if not status:
        return
    cols = st.columns(4)
    for col, label, value in zip(cols, ['Version','Workflow state','Next action','Human decision'],
                                 [status['version'],status['status'],status['next_action'],status['approval']]):
        col.metric(label, value.replace('_',' ').title())
    st.caption('Saved mode: '+(status['mode'] or 'no provider response recorded')+' · Policy revision '+str(status['policy_revision']))
    if status['planner_error']:
        st.error('Planner failed: '+status['planner_error']+'. No successful planner decision is inferred.')
    for error in status['errors'][-5:]:
        st.warning('Recorded error: '+str(error.get('error_code') or error.get('error') or error['event_type']))
    plan = status['planner'] if isinstance(status['planner'], dict) else {}
    if plan:
        st.subheader('Why these tests')
        st.text(plan.get('reason_summary', 'No decision summary recorded.'))
        st.caption('Selected: '+(', '.join(status['selected_test_ids']) or 'none'))
    if status['results']:
        st.dataframe([{'Test': r['test_id'], 'Outcome': r['status'], 'Latency (ms)': round(r['elapsed_ms'], 2),
                       'Issues': ', '.join(d['code'] for d in r['validation']['discrepancies']) or 'none'} for r in status['results']],
                     hide_index=True, width='stretch')
    else:
        st.info('No completed extraction results in this review.')
    with st.expander('Evidence and validation details'):
        st.json(redact({'source_refs': status['source_refs'], 'memory_supplied': status['supplied_memory_refs'],
                        'planner': status['planner'], 'results': status['results']}))
    with st.expander('Call measurements'):
        measured = perform(lambda: review_telemetry(settings.db_path, project, status['cycle_id'], checkpoint_path=settings.checkpoint_db_path))
        if measured:
            st.json(redact(measured))
    with st.expander('Resume saved work'):
        st.caption('Reuses the saved request and completed operations. A terminal failed planner is not resampled.')
        consent = st.checkbox('Allow any pending model requests to Google Gemini.', key='resume-consent-'+scope) if settings.mode=='live' else True
        if st.button('Resume review', key='resume-'+scope, disabled=bool(data['project']['archived_at'])):
            if not consent:
                st.error('Confirm pending live requests before resuming.')
            else:
                with st.spinner('Loading saved work…'):
                    if perform(lambda: Reviews(settings).resume(project, key)):
                        st.rerun()
    release_form(settings, project, status, scope, bool(data['project']['archived_at']))


def memory_page(data):
    st.title('Memory & feedback')
    st.write('Saved failures and developer decisions stay with their project across reviews and restarts.')
    if data['risks']:
        st.dataframe([{'Category': r['category'], 'State': r['status'], 'Last updated': r['updated_at'],
                       'Test': json.loads(r['evidence_json']).get('test_id', 'unspecified')} for r in data['risks']],
                     hide_index=True, width='stretch')
        with st.expander('Risk provenance'):
            st.json(redact(data['risks']))
    else:
        st.info('No failure memories saved for this project.')
    st.subheader('Developer feedback')
    if data['human_decisions']:
        st.dataframe(data['human_decisions'], hide_index=True, width='stretch')
    else:
        st.caption('No human release decisions recorded.')
    st.subheader('Recent activity')
    st.caption('Latest '+str(data['timeline_limit'])+' events maximum. Full history is available through CLI logs.')
    st.dataframe([{'Time (UTC)': e['created_at'], 'Event': e['event_type'], 'Record': e['ref_id']} for e in data['events']],
                 hide_index=True, width='stretch')


def policy_page(data):
    st.title('Evaluation policy')
    st.write('Inspect the rules used to score outputs. Proposed changes stay inactive until separately approved.')
    for policy in data['policies']:
        with st.container(border=True):
            st.subheader('Revision '+str(policy['revision'])+' · '+policy['status'].title())
            st.caption('Created '+policy['created_at']+' · Approved by '+(policy['approved_by'] or 'not yet approved'))
            st.json(redact(json.loads(policy['rules_json'])))
    st.caption('Use the policy propose/approve CLI commands for explicit corrections; release decisions do not change these criteria.')


def main():
    st.set_page_config(page_title='PromptPatch · Review workspace', page_icon='◈', layout='wide')
    st.markdown(STYLE, unsafe_allow_html=True)  # Static CSS only. No source/model/user value enters HTML.
    settings = perform(ui_settings)
    if settings is None:
        return
    with st.sidebar:
        st.title('◈ PromptPatch')
        st.caption('PROMPT REGRESSION WORKSPACE')
        execution = st.radio('Execution mode', ['replay', 'live'], index=0 if settings.mode=='replay' else 1,
                             format_func=lambda v: 'Offline replay' if v=='replay' else 'Live Gemini')
        st.caption('Replay is scripted. Live sends review data to Gemini only on explicit run/resume.')
    settings = settings.model_copy(update={'mode': execution})
    if not settings.db_path.is_file():
        setup(settings)
        return
    inventory = perform(lambda: projects(settings.db_path))
    if inventory is None:
        return
    if not inventory:
        setup(settings)
        return
    with st.sidebar:
        names = {p['id']: p['name']+(' · archived' if p['archived_at'] else '') for p in inventory}
        project = st.selectbox('Project', list(names), index=list(names).index('demo') if 'demo' in names else 0,
                               format_func=lambda p: names[p])
        page = st.radio('Workspace', ['Overview', 'Reviews', 'Memory & feedback', 'Policy'])
        st.divider()
        if st.button('Refresh saved state', width='stretch'):
            st.rerun()
        st.caption('Local owner workspace · No automatic release')
    data = perform(lambda: project_records(settings.db_path, project))
    listed = perform(lambda: list_reviews(settings.db_path, project))
    if data is None or listed is None:
        return
    scope = str(settings.db_path.resolve())+'-'+project
    if data['project']['archived_at']:
        st.warning('Archived project · history is available; new reviews and decisions are blocked.')
    if page=='Overview':
        overview(data, listed['reviews'])
    elif page=='Reviews':
        reviews_page(settings, project, data, listed['reviews'], scope)
    elif page=='Memory & feedback':
        memory_page(data)
    else:
        policy_page(data)


if __name__ == '__main__':
    main()
