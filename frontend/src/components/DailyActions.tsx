import { useEffect, useState } from 'react';
import { ArrowUpRight, CalendarClock } from 'lucide-react';
import type { Job, JobDocumentsInfo, NextAction } from '../types';
import { calendarDay, formatDate } from '../time';
import { useTimeSettings } from '../timeSettings';
import { nextSelection, partitionActions } from '../dailyQueue';
import { NextActionPanel } from './NextActionPanel';
import type { RecordedProgress } from './NextActionPanel';

const button = 'rounded-lg border border-ui-line-strong px-3 py-2 text-xs text-ui-secondary hover:bg-ui-raised disabled:opacity-50';
const external = (value?: string) => {
  try { const url = new URL(value || ''); return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined; }
  catch { return undefined; }
};

export function DailyActions({ items, refreshToken, onSelectJob, onRecorded }: {
  items: NextAction[]; refreshToken?: unknown; onSelectJob: (jobId: string) => void; onRecorded: () => Promise<void>;
}) {
  const { settings } = useTimeSettings();
  const [now, setNow] = useState(() => new Date());
  useEffect(() => { const timer = window.setInterval(() => setNow(new Date()), 60000); return () => window.clearInterval(timer); }, []);
  const groups = partitionActions(items, settings.timezone, now);
  const [view, setView] = useState<'today' | 'upcoming'>('today');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const [undo, setUndo] = useState<RecordedProgress>();
  const [undoBusy, setUndoBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [revision, setRevision] = useState(0);
  const [workingCopies, setWorkingCopies] = useState<Record<string, string>>({});
  const [prepared, setPrepared] = useState<Record<string, boolean>>({});
  const visible = groups[view];
  const navigationLocked = saving || reviewing || undoBusy;
  const selected = visible.find(item => item.application_id === selectedId) || visible[0];
  const today = calendarDay(now.toISOString(), settings.timezone)!;
  const dateLabel = (item: NextAction) => !item.date ? 'Confirm details'
    : `${item.date < today ? 'Overdue · ' : item.date === today ? 'Today · ' : ''}${formatDate(item.date, settings.timezone, { month: 'short', day: 'numeric' })}`;

  function saved(progress: RecordedProgress) {
      setUndo(progress.eventId ? progress : undefined);
      setNotice('Progress saved. The next action follows your confirmed record.');
  }

  async function recorded() {
    const next = selected ? nextSelection(visible, selected.application_id) : null;
    await onRecorded();
    setRevision(value => value + 1);
    setSelectedId(next);
  }

  async function undoLast() {
    if (!undo?.eventId) return;
    setUndoBusy(true);
    try {
      const response = await fetch(`/api/pipeline/applications/${encodeURIComponent(undo.applicationId)}/timeline/${encodeURIComponent(undo.eventId)}`, { method: 'DELETE' });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Could not undo this update.');
      setUndo(undefined);
      setNotice(`${result.message || 'Update undone.'} You can restore it from Deleted events in the application history.`);
      await onRecorded();
      setRevision(value => value + 1);
      setView('today'); setSelectedId(undo.applicationId);
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Could not undo this update.'); }
    finally { setUndoBusy(false); }
  }

  return <section aria-label="Daily workspace" className="overflow-hidden rounded-2xl border border-ui-line-soft bg-ui-panel/70">
    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-ui-line-soft p-5">
      <div>
        <h3 className="flex items-center gap-2 text-xl font-semibold text-ui-heading"><CalendarClock className="h-5 w-5 text-ui-ink-amber-400" /> Today’s work</h3>
        <p className="mt-2 text-xs text-ui-muted">{formatDate(today, settings.timezone, { weekday: 'long', month: 'long', day: 'numeric' })} · {groups.overdue} overdue · {settings.timezone}</p>
        <p className="mt-1 text-xs text-ui-muted">Choose a task, review its context, then record what happened.</p>
      </div>
      <div className="flex gap-2" aria-label="Task filters">
        <button disabled={navigationLocked} className={button} aria-pressed={view === 'today'} onClick={() => { setView('today'); setSelectedId(null); }}>Today & review ({groups.today.length})</button>
        <button disabled={navigationLocked} className={button} aria-pressed={view === 'upcoming'} onClick={() => { setView('upcoming'); setSelectedId(null); }}>Upcoming ({groups.upcoming.length})</button>
      </div>
    </div>
    {notice && <div role="status" className="flex flex-wrap items-center justify-between gap-2 border-b border-ui-line-soft bg-ui-fill-amber-950/20 px-5 py-3 text-xs text-ui-body">
      <span>{notice}</span>{undo?.eventId && <button disabled={undoBusy || saving} className={button} onClick={() => void undoLast()}>{undoBusy ? 'Undoing…' : 'Undo last update'}</button>}
    </div>}
    {!selected ? <p className="p-8 text-sm text-ui-muted">{view === 'today' ? 'No actions due or records awaiting review. Check Upcoming for your next dates.' : 'No upcoming actions scheduled. Paused applications remain in your pipeline.'}</p>
      : <div className="grid lg:grid-cols-[minmax(240px,0.8fr)_minmax(0,1.6fr)]">
        <nav aria-label="Daily tasks" className="max-h-[32rem] overflow-y-auto border-b border-ui-line-soft lg:max-h-[48rem] lg:border-b-0 lg:border-r">
          {visible.map(item => <button disabled={navigationLocked} key={item.application_id} onClick={() => setSelectedId(item.application_id)} aria-current={selected.application_id === item.application_id ? 'true' : undefined}
            className={`block w-full border-b border-ui-line-soft p-5 text-left transition hover:bg-ui-raised ${selected.application_id === item.application_id ? 'bg-ui-raised border-l-2 border-l-ui-ink-amber-400' : ''}`}>
            <span className="block text-xs font-medium text-ui-ink-amber-300">{dateLabel(item)}</span>
            <span className="mt-2 block text-sm font-semibold text-ui-heading">{item.company}</span>
            <span className="mt-1 block text-xs text-ui-body">{item.title}</span>
            <span className="mt-3 block text-xs text-ui-muted">{item.kind === 'record_review' ? 'Record review' : item.label}</span>
          </button>)}
        </nav>
        <div className="min-w-0 p-5 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0"><p className="text-xs font-medium text-ui-ink-amber-300">{dateLabel(selected)}</p><h4 className="mt-2 text-lg font-semibold text-ui-heading">{selected.label}</h4><p className="mt-1 text-sm text-ui-body">{selected.company} · {selected.title}</p></div>
            <button disabled={navigationLocked} className={`${button} flex items-center gap-1`} onClick={() => onSelectJob(selected.job_id)}>Full details <ArrowUpRight className="h-3 w-3" /></button>
          </div>
          <p className="mt-4 text-sm text-ui-body">{selected.reason}</p>
          {selected.due_date && <p className="mt-2 text-sm font-medium text-ui-ink-amber-300">{selected.kind === 'interview' || selected.kind === 'interview_review' ? 'Confirmed interview' : 'Confirmed deadline'}: {formatDate(selected.due_date, settings.timezone, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}</p>}
          <div className="mt-4 rounded-xl border border-ui-line-soft bg-ui-page/50 p-4">
            <NextActionPanel key={`${selected.application_id}:${revision}`} compact advance disabled={undoBusy} action={selected} currentStage={selected.current_stage || 'applied'} onRecorded={recorded} onSaved={saved} onBusyChange={setSaving} onReviewChange={setReviewing} />
          </div>
          {reviewing && <p className="mt-2 text-xs text-ui-muted">Choose how to continue tracking before moving to another task, or undo this update.</p>}
          <TaskContext key={`${selected.application_id}:${revision}`} refreshToken={refreshToken} action={selected} copies={workingCopies} setCopy={(id, value) => setWorkingCopies(current => ({ ...current, [id]: value }))}
            prepared={prepared} setPrepared={(id, value) => setPrepared(current => ({ ...current, [id]: value }))} />
        </div>
      </div>}
  </section>;
}

function TaskContext({ action, refreshToken, copies, setCopy, prepared, setPrepared }: {
  action: NextAction; refreshToken?: unknown; copies: Record<string, string>; setCopy: (id: string, value: string) => void;
  prepared: Record<string, boolean>; setPrepared: (id: string, value: boolean) => void;
}) {
  const { settings } = useTimeSettings();
  const [job, setJob] = useState<Job>();
  const [docs, setDocs] = useState<JobDocumentsInfo>();
  const [error, setError] = useState('');
  const [docsError, setDocsError] = useState(false);
  const [emails, setEmails] = useState<Array<{message_id: string; application_id: string; received_at: string; event_code: string}>>([]);
  const [emailError, setEmailError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  const [copyNotice, setCopyNotice] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setJob(undefined); setDocs(undefined); setDocsError(false); setEmails([]); setEmailError(false);
    async function load() {
      const request = async (path: string) => { const response = await fetch(path, { signal: controller.signal }); if (!response.ok) throw new Error('Could not load task context.'); return response.json(); };
      const [detail, documents, mail] = await Promise.allSettled([request(`/api/jobs/${encodeURIComponent(action.job_id)}`), request(`/api/jobs/${encodeURIComponent(action.job_id)}/documents`), request(`/api/gmail/messages?application_id=${encodeURIComponent(action.application_id)}`)]);
      if (controller.signal.aborted) return;
      if (detail.status === 'fulfilled') setJob(detail.value); else setError('Could not load this application’s context.');
      if (documents.status === 'fulfilled') setDocs(documents.value); else setDocsError(true);
      if (mail.status === 'fulfilled') setEmails((mail.value.messages || []).filter((message: {application_id: string}) => message.application_id === action.application_id)); else setEmailError(true);
      setLoading(false);
    }
    void load();
    return () => controller.abort();
  }, [action.job_id, action.application_id, refreshToken, retry]);

  if (loading) return <p role="status" className="mt-6 text-sm text-ui-muted">Loading application context…</p>;
  if (error) return <div role="alert" className="mt-6 text-sm text-ui-body">{error} <button className={button} onClick={() => setRetry(value => value + 1)}>Retry context</button></div>;
  if (!job) return null;
  const drafts = (job.contacts || []).flatMap(contact => (contact.messages || []).filter(message => ['draft', 'ready_to_send'].includes(message.status)).map(message => ({ ...message, contact })));
  const posting = external(job.job_url || job.application_url);
  return <div className="mt-6 space-y-5">
    {action.kind === 'interview' && <section aria-label="Interview preparation" className="rounded-xl border border-ui-line-soft p-4">
      <h5 className="text-sm font-semibold text-ui-heading">Prepare for the conversation</h5>
      <p className="mt-1 text-xs text-ui-muted">Session checklist · preparation does not record a completed interview.</p>
      {['Review the role and application documents', 'Choose evidence-backed examples to discuss', 'Prepare questions and confirm the meeting details'].map((label, index) => {
        const id = `${action.application_id}:${action.due_date}:${index}`;
        return <label key={id} className="mt-3 flex items-start gap-2 text-xs text-ui-body"><input type="checkbox" checked={!!prepared[id]} onChange={event => setPrepared(id, event.target.checked)} />{label}</label>;
      })}
    </section>}
    <section aria-label="Application context">
      <h5 className="text-sm font-semibold text-ui-heading">Application context</h5>
      <p className="mt-2 text-xs text-ui-muted">Stage: {(action.current_stage === 'knocked' ? 'Contacted' : action.current_stage || job.application?.current_stage || 'saved').replaceAll('_', ' ')} · Based on: {action.basis}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {posting && <a href={posting} target="_blank" rel="noopener noreferrer" className={button}>Open job posting</a>}
        {(['resume', 'cover_letter'] as const).map(type => docs?.[type]?.available && <a key={type} href={`/api/jobs/${encodeURIComponent(job.id)}/documents/${type === 'cover_letter' ? 'cover-letter' : 'resume'}?version=${encodeURIComponent(docs[type].latest_version || '')}`} target="_blank" rel="noopener noreferrer" className={button}>{type === 'resume' ? 'Resume' : 'Cover letter'} · {docs[type].latest_version}</a>)}
      </div>
      {docsError ? <p role="alert" className="mt-2 text-xs text-ui-ink-red-300">Documents could not be loaded. <button className="underline" onClick={() => setRetry(value => value + 1)}>Retry</button></p> : !docs?.has_documents && <p className="mt-2 text-xs text-ui-subtle">No published application documents.</p>}
      {job.job_description && <details className="mt-3 text-xs text-ui-muted"><summary className="cursor-pointer">Role description</summary><p className="mt-2 whitespace-pre-wrap break-words">{job.job_description}</p></details>}
    </section>
    <section aria-label="Matched application emails">
      <h5 className="text-sm font-semibold text-ui-heading">Matched emails</h5>
      <p className="mt-1 text-xs text-ui-muted">Recent saved matches for this application. Open the original to verify its context.</p>
      {emailError ? <p role="alert" className="mt-2 text-xs text-ui-ink-red-300">Email references could not be loaded. <button className="underline" onClick={() => setRetry(value => value + 1)}>Retry</button></p>
        : !emails.length ? <p className="mt-3 text-xs text-ui-subtle">No saved email matches. Use Gmail application updates to scan or review matches.</p>
        : <ul className="mt-3 space-y-2">{emails.slice(0, 5).map(mail => <li key={mail.message_id}><a href={`https://mail.google.com/mail/u/0/#all/${encodeURIComponent(mail.message_id)}`} target="_blank" rel="noopener noreferrer" className="text-xs text-ui-ink-amber-300 underline">{mail.event_code.replaceAll('_', ' ')} · {formatDate(mail.received_at, settings.timezone, { month: 'short', day: 'numeric' })} · Open original</a></li>)}</ul>}
    </section>
    <section aria-label="Existing outreach drafts">
      <h5 className="text-sm font-semibold text-ui-heading">Existing drafts</h5>
      <p className="mt-1 text-xs text-ui-muted">Working copies stay in this Dashboard session. Copying does not send or record progress. Check the context before using an earlier draft.</p>
      {!drafts.length && <p className="mt-3 text-xs text-ui-subtle">No existing draft for this application. Open Full details to prepare one.</p>}
      {drafts.map(draft => <details key={draft.id} className="mt-3 rounded-xl border border-ui-line-soft p-3">
        <summary className="cursor-pointer text-xs text-ui-body">{draft.contact.name} · {draft.channel}{draft.subject ? ` · ${draft.subject}` : ''}</summary>
        <label className="mt-3 block text-xs text-ui-muted">Working copy
          <textarea rows={7} value={copies[draft.id] ?? draft.body} onChange={event => setCopy(draft.id, event.target.value)} className="mt-2 w-full rounded-lg border border-ui-line bg-ui-page p-3 text-sm text-ui-body" />
        </label>
        <button className={`mt-2 ${button}`} onClick={async () => {
          try { await navigator.clipboard.writeText(copies[draft.id] ?? draft.body); setCopyNotice('Copied. Nothing has been sent or recorded.'); }
          catch { setCopyNotice('Copy failed. Select the working copy and copy it manually.'); }
        }}>Copy working text</button>
      </details>)}
      {copyNotice && <p role="status" className="mt-2 text-xs text-ui-muted">{copyNotice}</p>}
    </section>
    <section aria-label="Recent application history">
      <h5 className="text-sm font-semibold text-ui-heading">Recent history</h5>
      {!job.timeline?.length ? <p className="mt-3 text-xs text-ui-subtle">No confirmed events recorded.</p> : <ol className="mt-3 space-y-3">{job.timeline.slice(0, 5).map(event => <li key={event.id} className="border-l border-ui-line pl-3 text-xs"><p className="text-ui-body">{event.title}</p><p className="mt-1 text-ui-subtle">{formatDate(event.occurred_at, settings.timezone, { month: 'short', day: 'numeric', year: 'numeric' })}</p></li>)}</ol>}
    </section>
  </div>;
}
