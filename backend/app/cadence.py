"""Evidence-based next actions. Reads never alter stages or legacy reminders.

Confirmed cadence events live in the existing timeline, with structured dates.
No email content or inferred employer outcome is added to the data model.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import json
import uuid

from .clock import local_today, local_date_of, utc_now
from .database import get_db

EVENT_LABELS = {
    'application_submitted': 'Application submitted',
    'outreach_sent': 'Contacted',
    'follow_up': 'Follow-up sent',
    'message_received': 'Substantive reply received',
    'acknowledgement': 'Acknowledgement received',
    'interview_scheduled': 'Interview scheduled',
    'interview_completed': 'Interview completed',
    'thank_you_sent': 'Thank-you sent',
    'assessment_assigned': 'Assessment assigned',
    'assessment_submitted': 'Assessment submitted',
    'status_checked': 'Status checked',
    'cadence_paused': 'Paused',
    'cadence_resumed': 'Reminders resumed',
    'reminder_set': 'Reminder date set',
    'stage_updated': 'Progress updated',
}
LABELS = {
    'followup': 'Follow-up due', 'status_check': 'Status check due',
    'record_review': 'Record review', 'interview': 'Prepare for interview',
    'interview_review': 'Confirm interview outcome', 'thank_you': 'Send thank-you',
    'assessment': 'Complete assessment', 'paused': 'Paused', 'closed': 'Closed',
}


def business_days(start: date, count: int) -> date:
    step = 1 if count >= 0 else -1
    remaining = abs(count)
    while remaining:
        start += timedelta(days=step)
        if start.weekday() < 5:
            remaining -= 1
    return start


def event_day(value: str | None) -> date | None:
    """Calendar dates stay dates; historical naive instants are not guessed."""
    if not value:
        return None
    try:
        if len(value) == 10:
            parsed = date.fromisoformat(value)
        else:
            parsed = date.fromisoformat(local_date_of(value))
        return parsed if parsed.year >= 2000 else None
    except (ValueError, TypeError):
        return None


def _metadata(event):
    try:
        value = json.loads(event.get('metadata') or '{}')
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}



def visible_event(event):
    return not _metadata(dict(event)).get('_deleted_at')


def _application_state(conn, application_id):
    row = conn.execute('SELECT a.current_stage,a.outcome,a.applied_date,a.next_followup_date,j.status AS job_status FROM applications a JOIN jobs j ON j.id=a.job_id WHERE a.id=?', (application_id,)).fetchone()
    return dict(row) if row else None


def _restore_state(conn, application_id, state):
    now = utc_now().isoformat()
    conn.execute('UPDATE applications SET current_stage=?,outcome=?,applied_date=?,next_followup_date=?,updated_at=? WHERE id=?',
                 (state['current_stage'], state['outcome'], state['applied_date'], state['next_followup_date'], now, application_id))
    conn.execute('UPDATE jobs SET status=?,updated_at=? WHERE id=(SELECT job_id FROM applications WHERE id=?)', (state['job_status'], now, application_id))


def correct_timeline_event(application_id, event_id, restore=False):
    """Reversible local correction; never overwrite subsequent confirmed progress."""
    with get_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT * FROM timeline_events WHERE id=? AND application_id=?', (event_id, application_id)).fetchone()
        if not row:
            return None
        event = dict(row)
        meta = _metadata(event)
        deleted = bool(meta.get('_deleted_at'))
        if deleted == restore:
            state = _application_state(conn, application_id)
            stage_events = [dict(r) for r in conn.execute('SELECT * FROM timeline_events WHERE application_id=? AND to_stage IS NOT NULL ORDER BY julianday(occurred_at),rowid', (application_id,))]
            others_after = any(r['id'] != event_id and visible_event(r) for r in stage_events[stage_events.index(event) + 1:]) if event in stage_events else False
            if restore:
                correction = meta.get('_correction', {})
                if correction.get('stage_restored') and not others_after and state == correction.get('after'):
                    _restore_state(conn, application_id, correction['before'])
                meta.pop('_deleted_at', None)
                meta.pop('_correction', None)
                message = 'Timeline event restored.'
            else:
                before = meta.get('_stage_before')
                after = meta.get('_stage_after')
                restored_stage = False
                if before and after and not others_after and state == after:
                    earlier = stage_events[:stage_events.index(event)]
                    remaining = [r for r in earlier if visible_event(r)]
                    if remaining:
                        previous = _metadata(remaining[-1]).get('_stage_after') or before
                    else:
                        previous = next((_metadata(r).get('_stage_before') for r in stage_events if _metadata(r).get('_stage_before')), before)
                    if previous:
                        _restore_state(conn, application_id, previous)
                        restored_stage = True
                meta['_deleted_at'] = utc_now().isoformat()
                meta['_correction'] = {'before': state, 'after': _application_state(conn, application_id), 'stage_restored': restored_stage}
                message = 'Event deleted. Previous stage restored.' if restored_stage else 'Event deleted. Current stage kept.'
                if event.get('to_stage') and not restored_stage:
                    message += ' Review the stage if this was entered by mistake.'
            conn.execute('UPDATE timeline_events SET metadata=? WHERE id=?', (json.dumps(meta, sort_keys=True), event_id))
            conn.commit()
        else:
            message = 'Timeline event already restored.' if restore else 'Timeline event already deleted.'
        return {'event_id': event_id, 'message': message}

def next_action(application: dict, events: list[dict], messages: list[dict],
                contact_available: bool, today: date | None = None, *, include_preview=True) -> dict:
    today = today or local_today()
    result = {key: application.get(key) for key in ('job_id', 'company', 'title')}
    result.update(application_id=application['id'], kind='record_review',
                  label=LABELS['record_review'], date=None, due_date=None,
                  state='due', reason='', basis='', meaningful_date=None, followup_count=0,
                  current_stage=application['current_stage'], upcoming_actions=[])
    result['postponement_count'] = 0
    result.update(status_check_count=0, days_without_progress=0, status_review_required=False)
    progress_events = {'application_submitted', 'message_received', 'interview_scheduled',
                       'interview_completed', 'assessment_assigned', 'assessment_submitted',
                       'follow_up', 'thank_you_sent', 'status_checked'}
    for event in events:
        if not visible_event(event):
            continue
        if (event['event_type'] in progress_events or
            (event['event_type'] == 'stage_change' and event.get('from_stage') != event.get('to_stage'))):
            result['postponement_count'] = 0
        elif event['event_type'] == 'reminder_set' and _metadata(event).get('reminder_source') == 'later':
            result['postponement_count'] += 1

    def finish(kind, when=None, reason='', basis='', due=None):
        result.update(kind=kind, label=LABELS[kind],
                      date=when.isoformat() if when else None,
                      due_date=due.isoformat() if due else None,
                      reason=reason, basis=basis)
        result['state'] = ('paused' if kind == 'paused' else 'closed' if kind == 'closed'
                           else 'waiting' if when and when > today else 'due')
        result['status_review_required'] = result['status_review_required'] and kind in ('followup', 'status_check', 'paused')
        if include_preview:
            def preview(action_kind, action_date, condition):
                result['upcoming_actions'].append(dict(kind=action_kind, label=LABELS[action_kind],
                                                       date=action_date, condition=condition))
            if kind == 'thank_you':
                # Project the existing scheduler without persisting a hypothetical event.
                projected = next_action(application, [*events, dict(event_type='thank_you_sent',
                    occurred_at=anchor.isoformat())], messages, contact_available, today, include_preview=False)
                if projected['kind'] in ('followup', 'status_check'):
                    preview(projected['kind'], projected['date'], 'After the thank-you is recorded, if no substantive reply arrives.')
            elif kind in ('interview', 'interview_review'):
                preview('thank_you', None, 'After interview completion is confirmed; send within 24-48 hours.')
                preview('followup', None, 'After completion: employer response date +2 weekdays, otherwise interview +7 weekdays.')
            elif kind == 'assessment':
                preview('followup', None, 'After submission is confirmed: employer response date +2 weekdays, otherwise submission +7 weekdays.')
            elif kind == 'followup':
                if result['followup_count'] < 1:
                    preview('followup', None, 'If this follow-up is sent and remains unanswered: 7 weekdays after sending.')
                else:
                    preview('paused', None, 'If a second status follow-up is sent and remains unanswered; stage stays unchanged.')
            elif (kind == 'status_check' and result['followup_count'] == 0 and when
                  and when < anchor + timedelta(days=30)
                  and not any(e['event_type'] == 'status_checked' and
                              (event_day(e.get('occurred_at')) or date.min) >= anchor for e in events)):
                preview('status_check', (anchor + timedelta(days=30)).isoformat(),
                        'After the initial portal check is recorded, if there is no new progress.')
        return result

    stage = application['current_stage']
    if stage in ('closed', 'offer', 'saved'):
        inactive = finish('closed', reason='No application follow-up scheduled for this stage.')
        if stage != 'closed':
            inactive['label'] = 'No follow-up scheduled'
        return inactive

    # Row order is chronological, with insertion order resolving equal timestamps.
    significant = []
    for sequence, event in enumerate(events):
        kind = event['event_type']
        meta = dict(_metadata(event), _sequence=sequence)
        day = event_day(event.get('occurred_at'))
        if kind in ('outreach_sent', 'message_received', 'interview_scheduled',
                    'interview_completed', 'assessment_assigned', 'assessment_submitted',
                    'application_submitted'):
            if kind == 'outreach_sent' and any(entry[1] in ('interview_scheduled', 'interview_completed', 'assessment_assigned', 'assessment_submitted', 'stage_progress') for entry in significant):
                continue
            if kind != 'outreach_sent' or not any(entry[1] == 'outreach_sent' for entry in significant):
                significant.append((day, kind, meta, event.get('title', '')))
        elif (kind == 'stage_change' and event.get('from_stage') != event.get('to_stage')
              and event.get('to_stage') in ('recruiter_screen', 'assessment',
                                           'team_match', 'technical_interview', 'final_round')):
            significant.append((day, 'stage_progress', meta, event.get('title', '')))
    for message in messages:
        day = event_day(message.get('sent_at'))
        if message.get('channel') != 'linkedin_connect' and day and not any(entry[1] == 'outreach_sent' for entry in significant):
            significant.append((day, 'outreach_sent', {'contact_scope': 'cold'}, 'Contacted'))
    # Known events are compared by calendar day; timeline ordering handles same-day details.
    significant.sort(key=lambda entry: (entry[0] or date.min, entry[1] != 'stage_progress'))
    latest = significant[-1] if significant else None
    anchor = event_day(application.get('applied_date'))
    phase = 'application_submitted'
    meta = {}
    basis = 'Application submitted'
    if latest:
        anchor, phase, meta, event_title = latest
        basis = EVENT_LABELS.get(phase, event_title or 'Stage progressed')
    if not anchor:
        return finish('record_review', reason='Confirm the actual event date; the record has no reliable date.', basis=basis)
    result['meaningful_date'] = anchor.isoformat()
    cycle_checks = [e for index, e in enumerate(events) if e['event_type'] == 'status_checked'
                    and (event_day(e.get('occurred_at')) or date.min) >= anchor
                    and index > meta.get('_sequence', -1)]
    result['status_check_count'] = len(cycle_checks)
    result['days_without_progress'] = max(0, (today - anchor).days)
    expected = event_day(meta.get('expected_response_date'))
    review_after = event_day(meta.get('review_after'))
    result['status_review_required'] = (len(cycle_checks) >= 2 and result['days_without_progress'] >= 30
                                       and (not expected or today >= business_days(expected, 2))
                                       and (not review_after or today >= business_days(max(anchor, review_after), 10)))
    if stage == 'knocked' and phase == 'application_submitted':
        return finish('record_review', reason='Confirm whether outreach was sent and its actual date.', basis='Contacted stage without sent evidence')

    controls = [e for e in events if _metadata(e).get('cadence') and
                e['event_type'] in ('cadence_paused', 'cadence_resumed', 'reminder_set')]
    control = controls[-1] if controls else None
    control_day = event_day(control.get('occurred_at')) if control else None
    # A later substantive employer reply/progression reactivates a paused conversation.
    paused = bool(control and control['event_type'] == 'cadence_paused'
                  and (not latest or not control_day or anchor < control_day
                       or (anchor == control_day and meta.get('_sequence', -1) <= events.index(control))))
    if paused:
        result['status_review_required'] = False
    elif (control and control['event_type'] in ('cadence_resumed', 'reminder_set') and cycle_checks
          and events.index(control) > events.index(cycle_checks[-1])
          and (event_day(_metadata(control).get('action_date')) or date.min) > today):
        # A later explicit decision to wait should not immediately ask again.
        result['status_review_required'] = False

    followups = [e for e in events if e['event_type'] == 'follow_up'
                 and (event_day(e.get('occurred_at')) or date.min) >= anchor]
    # A same-day reply starts a new unanswered cycle, using actual timeline position.
    if latest and phase != 'outreach_sent':
        same_day_anchor = next((i for i in range(len(events)-1, -1, -1)
                               if events[i]['event_type'] == phase and event_day(events[i].get('occurred_at')) == anchor), -1)
        if same_day_anchor >= 0:
            followups = [e for e in events[same_day_anchor+1:] if e['event_type'] == 'follow_up']
    result['followup_count'] = len(followups)
    if paused:
        return finish('paused', reason='Active follow-ups are paused. The application stage and outcome are unchanged.', basis=basis)

    if phase == 'interview_scheduled':
        deadline = event_day(meta.get('due_date'))
        if not deadline:
            return finish('record_review', reason='Confirm the interview date from the original invitation.', basis=basis)
        if deadline < today:
            return finish('interview_review', deadline, 'Confirm whether the interview took place before planning a thank-you or follow-up.', basis, deadline)
        return finish('interview', business_days(deadline, -2), 'Prepare for the scheduled interview; application status follow-ups are suspended.', basis, deadline)
    if phase == 'assessment_assigned' or (stage == 'assessment' and phase == 'stage_progress'):
        deadline = event_day(meta.get('due_date'))
        if not deadline:
            return finish('record_review', reason='Confirm the assessment deadline and whether it has been submitted.', basis=basis)
        return finish('assessment', business_days(deadline, -2), 'Complete the assessment by the confirmed deadline.', basis, deadline)
    if phase == 'stage_progress':
        return finish('record_review', reason='Confirm the interview, reply or assessment details to schedule the next action.', basis=basis)

    if phase == 'interview_completed':
        thanks = any(e['event_type'] == 'thank_you_sent' and
                     (event_day(e.get('occurred_at')) or date.min) >= anchor for e in events)
        if not thanks:
            return finish('thank_you', anchor + timedelta(days=1), 'Send a brief thank-you within 24–48 hours; this is not a status follow-up.', basis)
    if not paused and len(followups) >= 2 and control and control['event_type'] in ('cadence_resumed', 'reminder_set'):
        when = event_day(_metadata(control).get('action_date'))
        return finish('status_check', when, 'The two-follow-up limit has been reached. Check the portal; further outreach awaits a substantive reply.', basis)
    if len(followups) >= 2:
        return finish('paused', reason='Active follow-ups are paused. The application stage and outcome are unchanged.', basis=basis)

    expected = event_day(meta.get('expected_response_date'))
    if expected:
        when = business_days(expected, 2)
    elif followups:
        when = business_days(event_day(followups[-1]['occurred_at']), 7)
    elif phase == 'application_submitted':
        review_after = event_day(meta.get('review_after'))
        when = business_days(max(anchor, review_after or anchor), 10)
    elif phase == 'outreach_sent':
        when = business_days(anchor, 5 if meta.get('contact_scope') == 'warm' else 7)
    elif phase == 'message_received':
        when = business_days(anchor, 5)
    else:
        when = business_days(anchor, 7)
    # Follow-ups already sent after a promise supersede that fulfilled reminder.
    if expected and followups and event_day(followups[-1]['occurred_at']) >= when:
        when = business_days(event_day(followups[-1]['occurred_at']), 7)

    if control and control['event_type'] != 'cadence_paused' and (not latest or not control_day or control_day >= anchor):
        when = event_day(_metadata(control).get('action_date')) or when
    usable_contact = contact_available or phase != 'application_submitted'
    kind = 'followup' if usable_contact else 'status_check'
    checks = [e for e in events if e['event_type'] == 'status_checked' and
              (event_day(e.get('occurred_at')) or date.min) >= anchor]
    if kind == 'status_check' and checks:
        if control and events.index(control) <= events.index(checks[-1]):
            control = None
        thirty_day = anchor + timedelta(days=30)
        if event_day(checks[-1]['occurred_at']) >= thirty_day and not control:
            return finish('paused', reason='Status reviewed. Resume reminders only if another check would help.', basis=basis)
        when = max(when, thirty_day)
        if control and control['event_type'] != 'cadence_paused':
            when = event_day(_metadata(control).get('action_date')) or when
    reason = ('A suitable contact is available; consider a concise status follow-up.' if kind == 'followup'
              else 'Check the application portal. No suitable contact is recorded; no email is required.')
    if today >= anchor + timedelta(days=30) and not followups:
        reason += ' No substantive progress recorded for 30 calendar days; this does not establish an outcome.'
    return finish(kind, when, reason, basis)


def schedules(conn) -> list[dict]:
    applications = [dict(row) for row in conn.execute('SELECT a.*,j.company,j.title FROM applications a JOIN jobs j ON j.id=a.job_id')]
    events = defaultdict(list)
    for row in conn.execute('SELECT * FROM timeline_events ORDER BY julianday(occurred_at),rowid'):
        if visible_event(row):
            events[row['application_id']].append(dict(row))
    messages = defaultdict(list)
    for row in conn.execute("SELECT m.*,c.job_id FROM outreach_messages m JOIN contacts c ON c.id=m.contact_id WHERE m.status IN ('sent','replied') ORDER BY julianday(m.sent_at)"):
        messages[row['job_id']].append(dict(row))
    contacts = {row['job_id'] for row in conn.execute("SELECT job_id FROM contacts WHERE trim(coalesce(email,'')) != '' OR trim(coalesce(linkedin_url,'')) != ''")}
    today = local_today()
    return [next_action(a, events[a['id']], messages[a['job_id']], a['job_id'] in contacts, today) for a in applications]


def get_schedule(application_id):
    with get_db() as conn:
        return next((item for item in schedules(conn) if item['application_id'] == application_id), None)


def attention(days_ahead=3):
    horizon = local_today() + timedelta(days=days_ahead) if days_ahead is not None else None
    with get_db() as conn:
        items = [item for item in schedules(conn) if item['state'] not in ('paused', 'closed')
                 and (horizon is None or not item['date'] or event_day(item['date']) <= horizon
                      or item['kind'] in ('interview', 'assessment'))]
    priority = {'interview_review': 0, 'interview': 0, 'assessment': 0, 'thank_you': 1,
                'record_review': 2, 'followup': 3, 'status_check': 4}
    return sorted(items, key=lambda item: (not item['date'], item['date'] or '',
                                          priority[item['kind']], item['company'], item['title']))


def record_event(application_id, event_type, occurred_at=None, **fields):
    if event_type not in EVENT_LABELS:
        raise ValueError('Choose a supported confirmed event')
    if fields.get('reminder_source') and event_type != 'reminder_set':
        raise ValueError('Later can only identify a reminder date change')
    instant = datetime.fromisoformat(occurred_at) if occurred_at else utc_now()
    if instant.tzinfo is None:
        raise ValueError('Event time must include its time zone')
    if instant.year < 2000 or instant > utc_now():
        raise ValueError('Record the actual past event time, not a future or invalid event')
    rounds = ('recruiter_screen', 'team_match', 'technical_interview', 'final_round')
    explicit_stage = fields.get('to_stage') if event_type == 'stage_updated' else None
    if event_type == 'stage_updated':
        if not explicit_stage:
            raise ValueError('Choose the confirmed stage')
        if explicit_stage == 'closed' and not fields.get('outcome'):
            raise ValueError('Choose the confirmed closing outcome')
        mapped = {'applied': 'application_submitted', 'knocked': 'outreach_sent', 'assessment': 'assessment_assigned'}
        event_type = 'interview_scheduled' if explicit_stage in rounds else mapped.get(explicit_stage, event_type)
        if explicit_stage in rounds:
            fields['interview_stage'] = explicit_stage
    if event_type == 'interview_scheduled' and fields.get('interview_stage') not in rounds:
        raise ValueError('Choose the confirmed interview round')
    required = {'interview_scheduled': 'due_date', 'assessment_assigned': 'due_date',
                'cadence_resumed': 'action_date', 'reminder_set': 'action_date'}
    if event_type in required and not fields.get(required[event_type]):
        raise ValueError('A confirmed date is required for this event')
    meta = {'cadence': True, **{k: v for k, v in fields.items() if v is not None}}
    for field in ('due_date', 'expected_response_date', 'action_date', 'review_after'):
        if meta.get(field) and not event_day(meta[field]):
            raise ValueError('Use a valid calendar date from year 2000 onward')
    if event_type in ('interview_scheduled', 'assessment_assigned') and event_day(meta['due_date']) < date.fromisoformat(local_date_of(instant.isoformat())):
        raise ValueError('The deadline cannot precede the scheduling event')
    with get_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        application = conn.execute('SELECT current_stage FROM applications WHERE id=?', (application_id,)).fetchone()
        if not application:
            return None
        occurred = instant.astimezone(timezone.utc).isoformat()
        encoded_meta = json.dumps(meta, sort_keys=True)
        candidates = conn.execute('SELECT * FROM timeline_events WHERE application_id=? AND event_type=? AND occurred_at=?', (application_id, event_type, occurred)).fetchall()
        if any(visible_event(row) and {k: v for k, v in _metadata(dict(row)).items() if not k.startswith('_')} == meta for row in candidates):
            return next(item for item in schedules(conn) if item['application_id'] == application_id)
        if event_type == 'follow_up':
            current = next(item for item in schedules(conn) if item['application_id'] == application_id)
            if current['state'] in ('closed', 'paused') or current['followup_count'] >= 2:
                raise ValueError('Resume a paused conversation before recording another follow-up')
        current_stage = application['current_stage']
        previous = conn.execute("SELECT * FROM timeline_events WHERE application_id=? AND (to_stage IS NOT NULL OR event_type IN ('assessment_assigned','interview_scheduled','application_submitted','outreach_sent'))", (application_id,)).fetchall()
        known = []
        for row in previous:
            if not visible_event(row):
                continue
            try:
                parsed = datetime.fromisoformat(row['occurred_at'])
                if parsed.tzinfo:
                    known.append(parsed)
            except (ValueError, TypeError):
                pass
        historical = bool(known and instant < max(known))
        target = explicit_stage
        if not target:
            if event_type == 'application_submitted' and current_stage in ('saved', 'applied'):
                target = 'applied'
            elif event_type == 'outreach_sent' and current_stage in ('saved', 'applied', 'knocked'):
                target = 'knocked'
            elif event_type in ('assessment_assigned', 'assessment_submitted') and current_stage in ('saved', 'applied', 'knocked', 'recruiter_screen', 'assessment'):
                target = 'assessment'
            elif event_type in ('interview_scheduled', 'interview_completed'):
                target = fields.get('interview_stage') or (current_stage if current_stage in rounds else None)
                if not target:
                    raise ValueError('Choose the confirmed interview round')
        if not historical and current_stage in ('closed', 'offer') and not explicit_stage and event_type in ('application_submitted', 'outreach_sent', 'assessment_assigned', 'assessment_submitted', 'interview_scheduled', 'interview_completed'):
            raise ValueError('Explicitly update the stage to reopen this record')
        synced_target = target if not historical else None
        if synced_target:
            meta['_stage_before'] = _application_state(conn, application_id)
            from .crud import _transition_application_stage
            _transition_application_stage(conn, application_id, synced_target, fields.get('outcome'), occurred_at=occurred, log_event=False)
            meta['_stage_after'] = _application_state(conn, application_id)
        encoded_meta = json.dumps(meta, sort_keys=True)
        event_id = str(uuid.uuid4())
        conn.execute('INSERT INTO timeline_events (id,application_id,event_type,title,occurred_at,metadata,from_stage,to_stage) VALUES (?,?,?,?,?,?,?,?)',
                     (event_id, application_id, event_type, EVENT_LABELS[event_type],
                      occurred, encoded_meta, current_stage if synced_target else None, synced_target))
        conn.commit()
        return {**next(item for item in schedules(conn) if item['application_id'] == application_id),
                'recorded_event_id': event_id}
