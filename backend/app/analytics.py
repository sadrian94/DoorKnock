"""Read-only application cohorts for Dashboard, not a current-stage funnel."""

import json
from collections import defaultdict
from datetime import date, timedelta
from statistics import median

from .cadence import event_day, visible_event

INTERVIEW_STAGES = {'recruiter_screen', 'team_match', 'technical_interview', 'final_round'}
OFFER_OUTCOMES = {'offer_accepted', 'offer_declined'}


def _milestones(event):
    kind, stage = event['event_type'], event['to_stage']
    if kind in ('interview_scheduled', 'interview_completed'):
        yield 'interview'
        if kind == 'interview_completed':
            yield 'completed'
    elif kind in ('stage_change', 'stage_updated'):
        if stage in INTERVIEW_STAGES:
            yield 'interview'
        elif stage == 'offer':
            yield 'offer'
        elif stage == 'closed':
            try:
                metadata = json.loads(event['metadata'] or '{}')
                if isinstance(metadata, dict) and metadata.get('outcome') in OFFER_OUTCOMES:
                    yield 'offer'
            except (ValueError, TypeError):
                pass


def application_analytics(conn, applications, today: date) -> dict:
    """Group by recorded application day; count later recorded outcomes per application."""
    milestones = defaultdict(lambda: defaultdict(set))
    events = conn.execute('''
        SELECT application_id, event_type, to_stage, occurred_at, metadata
        FROM timeline_events
        WHERE event_type IN ('interview_scheduled', 'interview_completed')
           OR (event_type IN ('stage_change', 'stage_updated') AND
               to_stage IN ('recruiter_screen', 'team_match', 'technical_interview',
                            'final_round', 'offer', 'closed'))
    ''')
    for event in events:
        if not visible_event(event):
            continue
        event_date = event_day(event['occurred_at'])
        if event_date and event_date <= today:
            for milestone in _milestones(event):
                milestones[event['application_id']][milestone].add(event_date)

    submitted = []
    records = []
    missing_dates = 0
    legacy_progress = 0
    for app in applications:
        history = milestones.get(app['id'], {})
        applied_day = event_day(app['applied_date'])
        stage, outcome = app['current_stage'], app['outcome']
        if not applied_day or applied_day > today:
            if (app['applied_date'] or stage in INTERVIEW_STAGES | {'applied', 'offer'}
                    or outcome in OFFER_OUTCOMES or history):
                missing_dates += 1
            continue
        first = {
            key: min((day for day in dates if day >= applied_day), default=None)
            for key, dates in history.items()
        }
        if ((stage in INTERVIEW_STAGES and not first.get('interview')) or
                ((stage == 'offer' or outcome in OFFER_OUTCOMES) and not first.get('offer'))):
            legacy_progress += 1
        submitted.append((applied_day, first))
        records.append({
            'job_id': app['job_id'], 'company': app['company'], 'title': app['title'],
            'applied_date': applied_day.isoformat(),
            'milestones': {key: day.isoformat() for key, day in first.items() if day is not None},
        })

    cohorts = {}
    for key, days in (('30d', 30), ('90d', 90), ('all', None)):
        start = today - timedelta(days=days - 1) if days else None
        cohort = [(day, first) for day, first in submitted if start is None or day >= start]
        times = [(first['interview'] - day).days for day, first in cohort if first.get('interview')]
        cohorts[key] = {
            'start_date': start.isoformat() if start else None,
            'applications': len(cohort),
            'with_interview': len(times),
            'with_completed_interview': sum(first.get('completed') is not None for _, first in cohort),
            'with_offer': sum(first.get('offer') is not None for _, first in cohort),
            'median_days_to_interview': median(times) if times else None,
        }
    return {
        'through_date': today.isoformat(),
        'cohorts': cohorts,
        'records': sorted(records, key=lambda row: (row['applied_date'], row['job_id']), reverse=True),
        'records_without_valid_applied_date': missing_dates,
        'dated_records_with_unverified_milestones': legacy_progress,
    }
