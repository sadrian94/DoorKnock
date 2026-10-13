import { useEffect, useState } from 'react';
import type { NextAction } from '../types';
import { defaultProgressEvent } from '../progressDefaults';
import { defaultReminderDate, formatDate } from '../time';
import { useTimeSettings } from '../timeSettings';

const EVENTS = [
  ['application_submitted', 'Application submitted'], ['outreach_sent', 'Contacted'],
  ['follow_up', 'Follow-up sent'], ['message_received', 'Substantive reply received'],
  ['acknowledgement', 'Acknowledgement received'], ['interview_scheduled', 'Interview scheduled'],
  ['interview_completed', 'Interview completed'], ['thank_you_sent', 'Thank-you sent'],
  ['assessment_assigned', 'Assessment assigned'], ['assessment_submitted', 'Assessment submitted'],
  ['status_checked', 'Status checked'], ['reminder_set', 'Set reminder date'],
  ['cadence_paused', 'Pause reminders'], ['cadence_resumed', 'Resume reminders'], ['stage_updated', 'Change stage / close application'],
];

function localInputNow() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

const ROUNDS = [['recruiter_screen', 'Recruiter screen'], ['team_match', 'Team interview'], ['technical_interview', 'Technical interview'], ['final_round', 'Final round']];
const STAGES = [['saved','Saved'], ['applied','Applied'], ['knocked','Contacted'], ['assessment','Assessment'], ...ROUNDS, ['offer','Offer'], ['closed','Closed']];

const DIRECT_ACTIONS = ['followup', 'status_check', 'thank_you', 'assessment', 'interview_review'];

export function NextActionPanel({ action, currentStage, onRecorded, compact = false }: { action: NextAction; currentStage: string; onRecorded: () => void | Promise<void>; compact?: boolean }) {
  const { settings } = useTimeSettings();
  const [open, setOpen] = useState(false);
  const [reviewAction, setReviewAction] = useState<NextAction | null>(null);
  const shownAction = reviewAction || action;
  const suggestedEvent = defaultProgressEvent(currentStage, shownAction.kind);
  const shortcut = (currentStage === 'saved' || (DIRECT_ACTIONS.includes(shownAction.kind) && !['closed', 'offer'].includes(currentStage)))
    ? EVENTS.find(([eventType]) => eventType === suggestedEvent) : undefined;
  const [event, setEvent] = useState(suggestedEvent);
  const [quick, setQuick] = useState(false);
  const [fromLater, setFromLater] = useState(false);
  const [dismissedCount, setDismissedCount] = useState(0);
  const [dismissedChecks, setDismissedChecks] = useState(0);
  const [occurred, setOccurred] = useState(localInputNow);
  const [deadline, setDeadline] = useState('');
  const [expected, setExpected] = useState('');
  const [scope, setScope] = useState('cold');
  const [round, setRound] = useState(ROUNDS.some(([key]) => key === currentStage) ? currentStage : '');
  const [stage, setStage] = useState(currentStage);
  const [outcome, setOutcome] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const needsDeadline = ['interview_scheduled', 'assessment_assigned', 'reminder_set', 'cadence_resumed'].includes(event) || (event === 'stage_updated' && (stage === 'assessment' || ROUNDS.some(([key]) => key === stage)));
  const hasExpected = ['message_received', 'interview_completed', 'assessment_submitted'].includes(event);
  const browserZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const displayDate = (value: string) => formatDate(value, settings.timezone, { month: 'short', day: 'numeric', year: 'numeric' });
  const postponements = shownAction.postponement_count || 0;
  const needsPostponementReview = postponements >= 2 && postponements > dismissedCount
    && !['closed', 'paused'].includes(shownAction.state);
  const statusChecks = shownAction.status_check_count || 0;
  const needsStatusReview = !!shownAction.status_review_required && statusChecks > dismissedChecks;
  const needsReview = needsPostponementReview || needsStatusReview;

  useEffect(() => {
    setReviewAction(null);
    if ((action.postponement_count || 0) < 2) setDismissedCount(0);
    if ((action.status_check_count || 0) < 2) setDismissedChecks(0);
  }, [action]);

  function start(eventType: string, isQuick: boolean) {
    setEvent(eventType); setQuick(isQuick); setOpen(true);
    setFromLater(eventType === 'reminder_set' && isQuick);
    setOccurred(localInputNow());
    setDeadline(eventType === 'reminder_set' ? defaultReminderDate(settings.timezone) : '');
    setExpected(''); setError('');
    setRound(ROUNDS.some(([key]) => key === currentStage) ? currentStage : '');
    setStage(currentStage); setOutcome('');
  }

  async function record() {
    setBusy(true);
    setError('');
    try {
      const payload: Record<string, string> = { event_type: event, occurred_at: new Date(occurred).toISOString() };
      if (event === 'interview_scheduled' || event === 'interview_completed') payload.interview_stage = round;
      if (event === 'stage_updated') { payload.to_stage = stage; if (stage === 'closed') payload.outcome = outcome; }
      if (needsDeadline) payload[['reminder_set', 'cadence_resumed'].includes(event) ? 'action_date' : 'due_date'] = deadline;
      if (event === 'reminder_set' && fromLater) payload.reminder_source = 'later';
      if (hasExpected && expected) payload.expected_response_date = expected;
      if (event === 'outreach_sent') payload.contact_scope = scope;
      if (event === 'application_submitted' && expected) payload.review_after = expected;
      let applicationId = action.application_id;
      if (!applicationId) {
        const started = await fetch(`/api/jobs/${encodeURIComponent(action.job_id)}/start-application`, { method: 'POST' });
        const application = await started.json();
        if (!started.ok || !application.id) throw new Error(typeof application.detail === 'string' ? application.detail : 'Could not create the application record.');
        applicationId = application.id;
      }
      const response = await fetch(`/api/pipeline/applications/${encodeURIComponent(applicationId)}/cadence`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Check the event and dates.');
      if ((event === 'reminder_set' && fromLater && result.postponement_count >= 2
           && !['closed', 'paused'].includes(result.state))
          || (event === 'status_checked' && result.status_review_required)) {
        // Keep the row mounted until the user reviews it, even if its new date
        // falls outside the Dashboard's attention window.
        setReviewAction(result);
        setOpen(false);
        return;
      }
      await onRecorded();
      setReviewAction(null);
      setOpen(false);
      setExpected('');
      setDeadline('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not record the event.');
    } finally { setBusy(false); }
  }

  async function keepWaiting() {
    setBusy(true); setError('');
    try {
      await onRecorded();
      setDismissedCount(postponements);
      setDismissedChecks(statusChecks);
      setReviewAction(null);
    } catch {
      setError('The reminder is saved. Refresh the application to reload its actions.');
    } finally { setBusy(false); }
  }

  return (
    <section className={compact ? "py-3" : "mx-6 my-3 rounded-xl border border-slate-700 bg-slate-900 p-4"} aria-label="Next action">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {!compact && <div>
          <p className="text-sm font-semibold text-amber-300">{shownAction.label}
            {shownAction.date && <span className="ml-2 text-slate-300">{displayDate(shownAction.date)}</span>}
            {shownAction.state === 'waiting' && <span className="ml-2 text-xs text-slate-500">Waiting for response</span>}
          </p>
          {action.due_date && <p className="mt-1 text-xs text-slate-300">{action.kind === 'interview' ? 'Interview' : 'Deadline'}: {displayDate(action.due_date)}</p>}
          <p className="mt-1 text-xs text-slate-400">{shownAction.reason}</p>
          <details className="mt-1 text-[11px] text-slate-500"><summary className="cursor-pointer">Why this date?</summary><p>Based on: {shownAction.basis || 'Current stage'} · {shownAction.followup_count}/2 status follow-ups · Later used {postponements} {postponements === 1 ? 'time' : 'times'} since last progress · {statusChecks} status checks since last substantive progress · dates use weekdays (Mon–Fri)</p></details>
        </div>}
        <div className="flex flex-wrap gap-2">
        {shortcut && <button disabled={busy} onClick={() => start(shortcut[0], true)} className="rounded-lg bg-amber-600 px-3 py-2 text-xs font-semibold text-white">{shortcut[1]}</button>}
        {shownAction.state !== 'closed' && <button disabled={busy} onClick={() => start(shownAction.state === 'paused' ? 'cadence_resumed' : 'reminder_set', true)} className="rounded-lg border border-slate-600 px-3 py-2 text-xs text-slate-200">{shownAction.state === 'paused' ? 'Resume' : 'Later'}</button>}
        <button disabled={busy} onClick={() => open ? setOpen(false) : start(suggestedEvent, false)} className="rounded-lg border border-slate-600 px-3 py-2 text-xs text-slate-200 hover:bg-slate-800">
          {open ? 'Cancel' : 'Update progress'}
        </button>
        </div>
      </div>
      {needsReview && !open && <div role="status" className="mt-3 rounded-lg border border-amber-800/60 bg-amber-950/20 p-3">
        <p className="text-sm text-amber-200">{needsStatusReview
          ? `You have checked the status ${statusChecks} times with no substantive progress for ${shownAction.days_without_progress} days. Keep tracking it?`
          : `You have postponed this application ${postponements} times. Keep tracking it?`}</p>
        <p className="mt-1 text-xs text-slate-400">{needsStatusReview
          ? 'The employer may not respond. This is a possibility, not a confirmed rejection or ghosting outcome.'
          : `${shownAction.date ? `Reminder saved for ${displayDate(shownAction.date)}. ` : ''}Postponing does not establish an employer outcome.`}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button disabled={busy} onClick={() => start('cadence_paused', true)} className="rounded border border-slate-600 px-3 py-2 text-xs text-slate-200">Pause tracking</button>
          <button disabled={busy} onClick={() => {
            if (needsStatusReview && shownAction.state === 'paused') {
              start('cadence_resumed', true); setDeadline(defaultReminderDate(settings.timezone));
            } else { void keepWaiting(); }
          }} className="rounded border border-slate-600 px-3 py-2 text-xs text-slate-200">Keep waiting</button>
          <button disabled={busy} onClick={() => { start('stage_updated', true); setStage('closed'); }} className="rounded border border-slate-600 px-3 py-2 text-xs text-slate-200">Close application</button>
        </div>
      </div>}
      {!open && error && <p role="alert" className="mt-2 text-xs text-red-300">{error}</p>}
      {!compact && !!action.upcoming_actions?.length && <div className="mt-3 border-t border-slate-700 pt-3">
        <p className="text-xs font-semibold text-slate-300">Coming next · tentative</p>
        <ul className="mt-2 space-y-2">{action.upcoming_actions.map((planned, index) => <li key={index} className="text-xs text-slate-400">
          <span className="text-slate-300">{planned.label} · {planned.date ? displayDate(planned.date) : 'Date pending confirmation'}</span>
          <p className="mt-1">{planned.condition}</p>
        </li>)}</ul>
      </div>}
      {open && <form onSubmit={(e) => { e.preventDefault(); void record(); }} className="mt-4 space-y-3 border-t border-slate-700 pt-4">
        <p className="text-xs text-slate-400">{quick ? 'Confirm what actually happened and its date before saving.' : 'Choose what happened. Saving updates your stage, timeline and next action together.'}</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-xs text-slate-300">What happened?
            <select required value={event} onChange={(e) => { setEvent(e.target.value); setFromLater(false); setDeadline(e.target.value === 'reminder_set' ? defaultReminderDate(settings.timezone) : ''); setExpected(''); }} className="mt-1 block w-full rounded border border-slate-600 bg-slate-950 p-2">
              <option value="">Choose what happened</option>
              <optgroup label="Progress">{EVENTS.filter(([value]) => !['reminder_set', 'cadence_paused', 'cadence_resumed', 'acknowledgement', 'stage_updated'].includes(value)).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</optgroup>
              <optgroup label="More options">{EVENTS.filter(([value]) => ['reminder_set', 'cadence_paused', 'cadence_resumed', 'acknowledgement', 'stage_updated'].includes(value)).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</optgroup>
            </select>
          </label>
          {(event === 'interview_scheduled' || event === 'interview_completed') && <label className="text-xs text-slate-300">Interview round
            <select required value={round} onChange={(e) => setRound(e.target.value)} className="mt-1 block w-full rounded border border-slate-600 bg-slate-950 p-2"><option value="">Choose round</option>{ROUNDS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>
          </label>}
          {event === 'stage_updated' && <label className="text-xs text-slate-300">Confirmed stage
            <select value={stage} onChange={(e) => setStage(e.target.value)} className="mt-1 block w-full rounded border border-slate-600 bg-slate-950 p-2">{STAGES.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>
          </label>}
          {event === 'stage_updated' && stage === 'closed' && <label className="text-xs text-slate-300">Confirmed outcome
            <select required value={outcome} onChange={(e) => setOutcome(e.target.value)} className="mt-1 block w-full rounded border border-slate-600 bg-slate-950 p-2"><option value="">Choose outcome</option>{['rejected', 'withdrawn', 'offer_accepted', 'offer_declined', 'ghosted'].map((key) => <option key={key} value={key}>{key.replaceAll('_', ' ')}</option>)}</select>
          </label>}
          {needsDeadline && <label className="text-xs text-slate-300">{['reminder_set', 'cadence_resumed'].includes(event) ? 'Next action date' : (event === 'interview_scheduled' || (event === 'stage_updated' && stage !== 'assessment')) ? 'Confirmed interview date' : 'Confirmed assessment deadline'}
            <input required type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} className="mt-1 block w-full rounded border border-slate-600 bg-slate-950 p-2" />
          </label>}
          {(hasExpected || event === 'application_submitted') && <label className="text-xs text-slate-300">{event === 'application_submitted' ? 'Posting closes / review starts after (optional)' : 'Employer response date (optional)'}
            <input type="date" value={expected} onChange={(e) => setExpected(e.target.value)} className="mt-1 block w-full rounded border border-slate-600 bg-slate-950 p-2" />
          </label>}
          {event === 'outreach_sent' && <label className="text-xs text-slate-300">Contact context
            <select value={scope} onChange={(e) => setScope(e.target.value)} className="mt-1 block w-full rounded border border-slate-600 bg-slate-950 p-2">
              <option value="cold">First outreach · 7 weekdays</option><option value="warm">Recruiter or referral contact · 5 weekdays</option>
            </select>
          </label>}
        </div>
        <details open={quick} className="text-xs text-slate-400"><summary className="cursor-pointer">Event date (defaults to now)</summary>          <label className="text-xs text-slate-300">Event time ({browserZone})
            <input required type="datetime-local" value={occurred} onChange={(e) => setOccurred(e.target.value)} className="mt-1 block w-full rounded border border-slate-600 bg-slate-950 p-2" />
          </label>
        </details>
        {error && <p role="alert" className="text-xs text-red-300">{error}</p>}
        <button disabled={busy} className="rounded-lg bg-amber-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{busy ? 'Saving…' : 'Save progress'}</button>
      </form>}
    </section>
  );
}
