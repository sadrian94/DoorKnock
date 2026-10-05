"""Observable scheduling and confirmation boundaries, using synthetic records."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import clock, crud
from app.database import get_db, init_db
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DOORKNOCK_DB_PATH", str(tmp_path / "cadence.db"))
    monkeypatch.setattr(clock, "SETTINGS_PATH", tmp_path / "time.json")
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            instant = datetime(2026, 10, 1, 15, tzinfo=timezone.utc)
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(clock, "datetime", FrozenDatetime)
    init_db()
    with get_db() as conn:
        conn.execute("INSERT INTO jobs (id,title,company) VALUES ('job','Analyst','Example')")
        conn.execute("""INSERT INTO applications
            (id,job_id,current_stage,applied_date,next_followup_date)
            VALUES ('application','job','applied','2026-09-25','2026-09-28')""")
        conn.commit()
    return TestClient(app)


def schedule(client):
    response = client.get('/api/pipeline/applications/application/cadence')
    assert response.status_code == 200
    return response.json()


def record(client, event_type, occurred_at='2026-10-01T14:00:00Z', **fields):
    if event_type == 'interview_scheduled':
        fields.setdefault('interview_stage', 'recruiter_screen')
    response = client.post('/api/pipeline/applications/application/cadence', json={
        'event_type': event_type, 'occurred_at': occurred_at, **fields})
    assert response.status_code == 200, response.text
    return response.json()


def test_cold_application_uses_ten_weekdays_and_preserves_legacy_reminder(client):
    action = schedule(client)
    assert (action['kind'], action['date']) == ('status_check', '2026-10-09')
    assert action['state'] == 'waiting'
    assert action['basis'] == 'Application submitted'
    with get_db() as conn:
        assert conn.execute("SELECT next_followup_date FROM applications").fetchone()[0] == '2026-09-28'


def test_draft_or_connection_invitation_is_not_contact_evidence(client):
    crud.transition_application_stage('application', 'knocked')
    assert schedule(client)['kind'] == 'record_review'
    record(client, 'outreach_sent', contact_scope='cold')
    action = schedule(client)
    assert (action['kind'], action['date']) == ('followup', '2026-10-12')


def test_two_unanswered_followups_pause_without_closing_then_reply_resets(client):
    record(client, 'outreach_sent', '2026-09-01T15:00:00Z', contact_scope='warm')
    record(client, 'follow_up', '2026-09-10T15:00:00Z')
    assert schedule(client)['date'] == '2026-09-21'
    record(client, 'follow_up', '2026-09-21T15:00:00Z')
    assert schedule(client)['state'] == 'paused'
    assert not client.get('/api/pipeline/dashboard').json()['attention_items']
    with get_db() as conn:
        assert conn.execute('SELECT current_stage,outcome FROM applications').fetchone()[:] == ('knocked', None)
    record(client, 'message_received', expected_response_date='2026-10-09')
    assert schedule(client)['date'] == '2026-10-13'
    assert schedule(client)['followup_count'] == 0


def test_acknowledgement_and_notes_do_not_reset_waiting_period(client):
    first = schedule(client)
    record(client, 'acknowledgement')
    with get_db() as conn:
        conn.execute("UPDATE applications SET updated_at='2026-10-01T15:00:00Z'")
        conn.commit()
    assert schedule(client)['date'] == first['date']


def test_interview_and_assessment_have_actions_even_outside_old_followup_stages(client):
    record(client, 'interview_scheduled', due_date='2026-10-02')
    action = schedule(client)
    assert action['kind'] == 'interview'
    assert action['due_date'] == '2026-10-02'
    record(client, 'interview_completed')
    assert schedule(client)['kind'] == 'thank_you'
    record(client, 'thank_you_sent')
    assert schedule(client)['date'] == '2026-10-12'
    crud.transition_application_stage('application', 'assessment')
    record(client, 'assessment_assigned', due_date='2026-10-07')
    action = schedule(client)
    assert (action['kind'], action['date'], action['due_date']) == ('assessment', '2026-10-05', '2026-10-07')
    assert client.get('/api/pipeline/dashboard').json()['attention_items'][0]['kind'] == 'assessment'


def test_pause_override_and_resume_are_independent_of_stage(client):
    record(client, 'reminder_set', action_date='2026-10-02')
    assert schedule(client)['date'] == '2026-10-02'
    record(client, 'cadence_paused')
    assert schedule(client)['state'] == 'paused'
    record(client, 'cadence_resumed', action_date='2026-10-05')
    assert schedule(client)['date'] == '2026-10-05'


@pytest.mark.parametrize('payload', [
    {'event_type':'interview_scheduled'},
    {'event_type':'follow_up','occurred_at':'2026-10-01T10:00:00'},
    {'event_type':'message_received','expected_response_date':'invalid'},
    {'event_type':'cadence_resumed'},
])
def test_invalid_confirmation_never_writes_event(client, payload):
    response = client.post('/api/pipeline/applications/application/cadence', json=payload)
    assert response.status_code in (400, 422)
    with get_db() as conn:
        assert conn.execute('SELECT count(*) FROM timeline_events').fetchone()[0] == 0


def test_status_checks_do_not_repeat_and_unknown_dates_are_reviewed(client):
    with get_db() as conn:
        conn.execute("UPDATE applications SET applied_date='2026-08-01',updated_at='2026-10-01T15:00:00Z'")
        conn.commit()
    assert schedule(client)['kind'] == 'status_check'
    record(client, 'status_checked')
    assert schedule(client)['state'] == 'paused'
    with get_db() as conn:
        conn.execute("UPDATE applications SET applied_date='1970-01-21T11:05:03.652000',current_stage='knocked'")
        conn.commit()
    record(client, 'cadence_resumed', action_date='2026-10-05')
    assert schedule(client)['kind'] == 'record_review'


def test_same_day_reply_after_pause_reactivates_and_repeat_outreach_does_not_reset_limit(client):
    record(client, 'outreach_sent', '2026-09-01T15:00:00Z')
    record(client, 'follow_up', '2026-09-10T15:00:00Z')
    record(client, 'follow_up', '2026-09-21T15:00:00Z')
    record(client, 'outreach_sent', '2026-09-25T15:00:00Z')
    assert schedule(client)['state'] == 'paused'
    record(client, 'cadence_paused', '2026-10-01T10:00:00Z')
    record(client, 'message_received', '2026-10-01T12:00:00Z')
    assert schedule(client)['state'] == 'waiting'


def test_resume_after_limit_permits_portal_check_not_more_automatic_followups(client):
    record(client, 'outreach_sent', '2026-09-01T15:00:00Z')
    record(client, 'follow_up', '2026-09-10T15:00:00Z')
    record(client, 'follow_up', '2026-09-21T15:00:00Z')
    record(client, 'cadence_resumed', action_date='2026-10-05')
    assert (schedule(client)['kind'], schedule(client)['date']) == ('status_check', '2026-10-05')
    assert client.post('/api/pipeline/applications/application/cadence', json={'event_type':'follow_up'}).status_code == 400


def test_finished_status_check_consumes_an_old_manual_override(client):
    with get_db() as conn:
        conn.execute("UPDATE applications SET applied_date='2026-08-01'")
        conn.commit()
    record(client, 'reminder_set', '2026-09-20T15:00:00Z', action_date='2026-09-30')
    record(client, 'status_checked')
    assert schedule(client)['state'] == 'paused'


@pytest.mark.parametrize('stage', ['saved', 'offer'])
def test_inactive_schedule_does_not_mislabel_saved_or_offer_as_closed(client, stage):
    crud.transition_application_stage('application', stage)
    assert schedule(client)['label'] == 'No follow-up scheduled'


def test_retrying_same_confirmed_event_does_not_count_two_followups(client):
    record(client, 'outreach_sent', '2026-09-01T15:00:00Z')
    record(client, 'follow_up', '2026-09-10T15:00:00Z')
    record(client, 'follow_up', '2026-09-10T15:00:00Z')
    assert schedule(client)['followup_count'] == 1
    with get_db() as conn:
        assert conn.execute("SELECT count(*) FROM timeline_events WHERE event_type='follow_up'").fetchone()[0] == 1


def test_assessment_update_sets_stage_and_deadline_in_one_history_entry(client):
    record(client, 'assessment_assigned', due_date='2026-10-07')
    job = client.get('/api/jobs/job').json()
    assert job['application']['current_stage'] == 'assessment'
    assert job['status'] == 'in_progress'
    assert job['next_action']['kind'] == 'assessment'
    assert len(job['timeline']) == 1
    assert (job['timeline'][0]['from_stage'], job['timeline'][0]['to_stage']) == ('applied', 'assessment')
    record(client, 'assessment_submitted', '2026-10-01T14:30:00Z')
    job = client.get('/api/jobs/job').json()
    assert job['application']['current_stage'] == 'assessment'
    assert job['next_action']['kind'] == 'followup'


def test_selected_interview_round_is_synced_and_completion_retains_it(client):
    record(client, 'interview_scheduled', due_date='2026-10-02', interview_stage='technical_interview')
    assert client.get('/api/jobs/job').json()['application']['current_stage'] == 'technical_interview'
    record(client, 'interview_completed', '2026-10-01T14:30:00Z')
    assert client.get('/api/jobs/job').json()['application']['current_stage'] == 'technical_interview'
    assert schedule(client)['kind'] == 'thank_you'


def test_stage_and_event_roll_back_together_when_history_cannot_be_written(client):
    import sqlite3
    with get_db() as conn:
        conn.execute("""CREATE TRIGGER fail_history BEFORE INSERT ON timeline_events
                        BEGIN SELECT RAISE(ABORT, 'synthetic history failure'); END""")
        conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        record(client, 'assessment_assigned', due_date='2026-10-07')
    with get_db() as conn:
        assert conn.execute('SELECT current_stage FROM applications').fetchone()[0] == 'applied'
        assert conn.execute('SELECT count(*) FROM timeline_events').fetchone()[0] == 0


def test_historical_progress_does_not_regress_current_stage(client):
    record(client, 'interview_scheduled', due_date='2026-10-02', interview_stage='final_round')
    record(client, 'assessment_assigned', '2026-09-20T15:00:00Z', due_date='2026-09-25')
    assert client.get('/api/jobs/job').json()['application']['current_stage'] == 'final_round'
    assert schedule(client)['kind'] == 'interview'


@pytest.mark.parametrize('payload', [
    {'event_type': 'interview_scheduled', 'due_date': '2026-10-02'},
    {'event_type': 'stage_updated', 'to_stage': 'closed'},
    {'event_type': 'stage_updated', 'to_stage': 'assessment'},
    {'event_type': 'stage_updated', 'to_stage': 'technical_interview'},
])
def test_incomplete_progress_update_never_changes_stage(client, payload):
    response = client.post('/api/pipeline/applications/application/cadence', json=payload)
    assert response.status_code in (400, 422)
    with get_db() as conn:
        assert conn.execute('SELECT current_stage FROM applications').fetchone()[0] == 'applied'
        assert conn.execute('SELECT count(*) FROM timeline_events').fetchone()[0] == 0


def test_generic_stage_update_uses_same_assessment_flow_and_confirmed_close(client):
    record(client, 'stage_updated', to_stage='assessment', due_date='2026-10-07')
    assert schedule(client)['kind'] == 'assessment'
    record(client, 'stage_updated', '2026-10-01T14:30:00Z', to_stage='closed', outcome='withdrawn')
    with get_db() as conn:
        assert conn.execute('SELECT current_stage,outcome FROM applications').fetchone()[:] == ('closed', 'withdrawn')
    assert schedule(client)['state'] == 'closed'


def test_contact_updates_do_not_regress_an_interview_or_reopen_closed_records(client):
    record(client, 'interview_scheduled', due_date='2026-10-02', interview_stage='final_round')
    record(client, 'outreach_sent', '2026-10-01T14:30:00Z')
    assert client.get('/api/jobs/job').json()['application']['current_stage'] == 'final_round'
    assert client.get('/api/pipeline/applications/application/cadence').json()['kind'] == 'interview'
    crud.transition_application_stage('application', 'closed', outcome='rejected')
    response = client.post('/api/pipeline/applications/application/cadence', json={
        'event_type': 'assessment_assigned', 'due_date':'2026-10-07'})
    assert response.status_code == 400
    with get_db() as conn:
        assert conn.execute('SELECT current_stage,outcome FROM applications').fetchone()[:] == ('closed', 'rejected')


def latest_event_id(client):
    return client.get('/api/jobs/job').json()['timeline'][0]['id']


def delete_event(client, event_id, application='application'):
    return client.delete(f'/api/pipeline/applications/{application}/timeline/{event_id}')


def test_delete_wrong_progress_restores_stage_and_schedule_and_undo(client):
    baseline = schedule(client)
    record(client, 'assessment_assigned', due_date='2026-10-07')
    event_id = latest_event_id(client)
    result = delete_event(client, event_id)
    assert result.status_code == 200
    job = client.get('/api/jobs/job').json()
    assert job['timeline'] == []
    assert job['application']['current_stage'] == 'applied'
    assert schedule(client) == baseline
    with get_db() as conn:
        assert conn.execute('SELECT COUNT(*) FROM timeline_events').fetchone()[0] == 1
    restored = client.post(f'/api/pipeline/applications/application/timeline/{event_id}/restore')
    assert restored.status_code == 200
    job = client.get('/api/jobs/job').json()
    assert len(job['timeline']) == 1
    assert job['application']['current_stage'] == 'assessment'
    assert schedule(client)['kind'] == 'assessment'


def test_delete_followup_recomputes_count_and_is_idempotent(client):
    record(client, 'outreach_sent')
    record(client, 'follow_up', '2026-10-01T14:30:00Z')
    event_id = latest_event_id(client)
    assert schedule(client)['followup_count'] == 1
    assert delete_event(client, event_id).status_code == 200
    assert delete_event(client, event_id).status_code == 200
    assert schedule(client)['followup_count'] == 0
    assert client.get('/api/jobs/job').json()['application']['current_stage'] == 'knocked'


def test_deleting_older_progress_and_restoring_cannot_overwrite_newer_stage(client):
    record(client, 'assessment_assigned', due_date='2026-10-07')
    older = latest_event_id(client)
    record(client, 'interview_scheduled', '2026-10-01T14:30:00Z', due_date='2026-10-08', interview_stage='final_round')
    assert delete_event(client, older).status_code == 200
    assert client.post(f'/api/pipeline/applications/application/timeline/{older}/restore').status_code == 200
    assert client.get('/api/jobs/job').json()['application']['current_stage'] == 'final_round'


def test_timeline_delete_is_scoped_to_the_application(client):
    record(client, 'assessment_assigned', due_date='2026-10-07')
    event_id = latest_event_id(client)
    assert delete_event(client, event_id, 'wrong-application').status_code == 404
    assert len(client.get('/api/jobs/job').json()['timeline']) == 1


def test_undo_after_new_progress_does_not_restore_old_stage(client):
    record(client, 'assessment_assigned', due_date='2026-10-07')
    event_id = latest_event_id(client)
    assert delete_event(client, event_id).status_code == 200
    record(client, 'interview_scheduled', '2026-10-01T14:30:00Z', due_date='2026-10-08', interview_stage='final_round')
    assert client.post(f'/api/pipeline/applications/application/timeline/{event_id}/restore').status_code == 200
    assert client.get('/api/jobs/job').json()['application']['current_stage'] == 'final_round'


def test_delete_stage_chain_returns_to_original_state(client):
    record(client, 'assessment_assigned', due_date='2026-10-07')
    older = latest_event_id(client)
    record(client, 'interview_scheduled', '2026-10-01T14:30:00Z', due_date='2026-10-08', interview_stage='final_round')
    newer = latest_event_id(client)
    assert delete_event(client, older).status_code == 200
    assert delete_event(client, newer).status_code == 200
    job = client.get('/api/jobs/job').json()
    assert job['application']['current_stage'] == 'applied'
    assert len(job['deleted_timeline']) == 2


def test_legacy_stage_event_deletion_preserves_stage_and_can_be_restored(client):
    crud.transition_application_stage('application', 'closed', outcome='rejected')
    event_id = latest_event_id(client)
    result = delete_event(client, event_id)
    assert result.status_code == 200
    assert 'Review the stage' in result.json()['message']
    job = client.get('/api/jobs/job').json()
    assert job['application']['current_stage'] == 'closed'
    assert job['application']['outcome'] == 'rejected'
    assert job['timeline'] == []
    assert len(job['deleted_timeline']) == 1
    assert client.post(f'/api/pipeline/applications/application/timeline/{event_id}/restore').status_code == 200
    assert len(client.get('/api/jobs/job').json()['timeline']) == 1


def test_delete_confirmed_close_restores_previous_outcome_and_status(client):
    record(client, 'stage_updated', to_stage='closed', outcome='withdrawn')
    event_id = latest_event_id(client)
    assert delete_event(client, event_id).status_code == 200
    job = client.get('/api/jobs/job').json()
    assert job['application']['current_stage'] == 'applied'
    assert job['application']['outcome'] is None
    assert client.post(f'/api/pipeline/applications/application/timeline/{event_id}/restore').status_code == 200
    job = client.get('/api/jobs/job').json()
    assert job['application']['outcome'] == 'withdrawn'
    assert job['status'] == 'archived'


def test_new_progress_after_legacy_stage_can_be_undone(client):
    crud.transition_application_stage('application', 'knocked')
    with get_db() as conn:
        conn.execute("UPDATE timeline_events SET occurred_at='2026-09-30T15:00:00Z' WHERE event_type='stage_change'")
        conn.commit()
    record(client, 'assessment_assigned', due_date='2026-10-07')
    event_id = latest_event_id(client)
    assert delete_event(client, event_id).status_code == 200
    assert client.get('/api/jobs/job').json()['application']['current_stage'] == 'knocked'
