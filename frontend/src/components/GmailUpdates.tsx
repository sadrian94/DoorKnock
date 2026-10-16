import React, { useEffect, useRef, useState } from 'react';
import { GmailMessagePreview } from './GmailMessagePreview';
import { Mail, ArrowUpRight, Check, ChevronRight, Search, Undo2 } from 'lucide-react';
import { useTimeSettings } from '../timeSettings';
import { calendarDay, formatDate, formatDateTime } from '../time';
import { advanceScanProgress, readScanProgress, scanProgressFresh, writeScanProgress } from '../gmailScanProgress';
import type { ScanBatch, ScanProgress } from '../gmailScanProgress';
import { applicationChoices, mergeReviews, nextReviewId, readReviewWorkspace, writeReviewWorkspace } from '../gmailReviewWorkspace';
import type { GmailApplication, GmailReview, ReviewChoice, ReviewView, ReviewWorkspace } from '../gmailReviewWorkspace';

const eventLabels: Record<string, string> = {
  application_received: 'Application received', recruiter_screen_scheduled: 'Recruiter screen scheduled',
  rejected: 'Application declined', related: 'Related message',
};
const reasonLabels: Record<string, string> = {
  multiple_applications: 'Several applications could match. Confirm the correct role.',
  no_application_match: 'No application matched clearly. Choose the application this email concerns.',
  unclear_event: 'The email does not clearly confirm a stage. You can save its link without changing progress.',
  bulk_or_automated: 'Automated message. Check the original before recording progress.',
  older_message: 'This email predates the recorded application. Check its date before updating progress.',
  stage_conflict: 'The suggested stage differs from the current record. Check later progress first.',
  company_only: 'The company matches, but the email does not include the exact role. Confirm the application.',
  thread_context: 'This conversation contains a confirmed application message. Check this new reply.',
  human_confirmation_required: 'Check the original email, then save its link or confirm the progress it supports.',
};
const shortReasons: Record<string, string> = {
  company_only: 'Company match', thread_context: 'Same conversation', multiple_applications: 'Choose application',
  no_application_match: 'Match needed', stage_conflict: 'Check current stage', older_message: 'Older email',
};
const statusLabels: Record<string, string> = { linked: 'Link saved', applied: 'Review confirmed', dismissed: 'Dismissed' };
const stages = ['saved', 'applied', 'knocked', 'recruiter_screen', 'assessment', 'team_match', 'technical_interview', 'final_round', 'offer', 'closed'];
const datedStages = ['assessment', 'recruiter_screen', 'team_match', 'technical_interview', 'final_round'];
const stageLabel = (value: string) => value === 'knocked' ? 'Contacted' : value.replaceAll('_', ' ');
const buttonClass = 'rounded-lg border border-ui-line px-3 py-2 text-sm text-ui-body transition hover:bg-ui-raised focus-visible:outline focus-visible:outline-2 focus-visible:outline-ui-ink-amber-500 disabled:opacity-50';
const primaryClass = 'inline-flex items-center justify-center gap-2 rounded-lg bg-ui-fill-amber-600 px-4 py-2.5 text-sm font-semibold text-ui-on-action transition hover:bg-ui-fill-amber-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ui-ink-amber-400 disabled:opacity-50';
const textButton = 'text-left text-sm text-ui-ink-amber-400 underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-ui-ink-amber-500 disabled:opacity-50';
const originalUrl = (item: GmailReview) => `https://mail.google.com/mail/u/0/#all/${encodeURIComponent(item.message_id)}`;
const readJson = async (response: Response) => {
  if (!response.headers.get('content-type')?.includes('application/json')) throw new Error(`Server error (${response.status}). Check the DoorKnock backend log.`);
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : `Request failed (${response.status})`);
  return result;
};

type ReviewPage = { reviews: GmailReview[]; applications: GmailApplication[]; pending_count: number; processed_count: number; has_more: boolean; next_offset: number };
type Props = { onApplicationsChanged: () => Promise<void>; onOpenSettings: () => void };
export const GmailUpdates: React.FC<Props> = ({ onApplicationsChanged, onOpenSettings }) => {
  const { settings } = useTimeSettings();
  const [initial] = useState<ReviewWorkspace>(() => {
    try { return readReviewWorkspace(window.sessionStorage); } catch { return { view: 'pending', selectedId: null, choices: {} }; }
  });
  const [view, setView] = useState<ReviewView>(initial.view);
  const [selectedId, setSelectedId] = useState(initial.selectedId);
  const [choices, setChoices] = useState(initial.choices);
  const [pages, setPages] = useState<Record<ReviewView, GmailReview[]>>({ pending: [], processed: [] });
  const [counts, setCounts] = useState({ pending: 0, processed: 0 });
  const [pagination, setPagination] = useState<Record<ReviewView, { hasMore: boolean; offset: number }>>({ pending: { hasMore: false, offset: 0 }, processed: { hasMore: false, offset: 0 } });
  const [applications, setApplications] = useState<GmailApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewsLoading, setReviewsLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [configured, setConfigured] = useState(false);
  const [reconnect, setReconnect] = useState(false);
  const [scanBusy, setScanBusy] = useState<'latest' | 'older' | ''>('');
  const [reviewBusy, setReviewBusy] = useState('');
  const [message, setMessage] = useState('');
  const [lastUndo, setLastUndo] = useState<GmailReview | null>(null);
  const [changingApplication, setChangingApplication] = useState(false);
  const [query, setQuery] = useState('');
  const [scanProgress, setScanProgress] = useState<ScanProgress | null>(() => {
    try { return readScanProgress(window.sessionStorage); } catch { return null; }
  });
  const [days, setDays] = useState(scanProgress?.days || 14);
  const [limit, setLimit] = useState(scanProgress?.limit || 150);
  const [lastBatch, setLastBatch] = useState<ScanBatch | null>(null);
  const [checkedAt, setCheckedAt] = useState('');
  const requestVersion = useRef(0);
  const queueRef = useRef<HTMLElement>(null);
  const locked = loading || reviewsLoading || Boolean(scanBusy) || Boolean(reviewBusy);
  const rows = pages[view];
  const selected = rows.find(item => item.message_id === selectedId) || rows[0];
  const choice = selected ? choices[selected.message_id] : undefined;
  const selectedApplication = applications.find(app => app.id === (view === 'processed' ? selected?.application_id : choice?.applicationId));
  const validRange = Number.isInteger(days) && days >= 1 && days <= 30 && Number.isInteger(limit) && limit >= 100 && limit <= 200;
  const hasOlder = Boolean(scanProgress?.nextPage);

  useEffect(() => {
    const queue = queueRef.current;
    const button = queue?.querySelector<HTMLElement>('[aria-pressed="true"]');
    if (!queue || !button) return;
    const alignSelection = () => {
      const bounds = queue.getBoundingClientRect();
      const selectedBounds = button.getBoundingClientRect();
      if (selectedBounds.top < bounds.top) queue.scrollTop -= bounds.top - selectedBounds.top;
      else if (selectedBounds.bottom > bounds.bottom) queue.scrollTop += selectedBounds.bottom - bounds.bottom;
    };
    alignSelection();
    const observer = new ResizeObserver(alignSelection);
    observer.observe(queue);
    return () => observer.disconnect();
  }, [selected?.message_id, rows]);

  function saveScan(progress: ScanProgress | null) {
    setScanProgress(progress);
    try { writeScanProgress(window.sessionStorage, progress); } catch { /* Optional storage. */ }
  }
  useEffect(() => {
    if (loading || reviewsLoading) return;
    try { writeReviewWorkspace(window.sessionStorage, { view, selectedId, choices, loaded: pagination[view].offset || 50 }); } catch { /* Optional storage. */ }
  }, [view, selectedId, choices, pagination, loading, reviewsLoading]);

  async function loadReviews(target: ReviewView, append = false, ensureId: string | null = null): Promise<ReviewPage | null> {
    const version = ++requestVersion.current;
    setReviewsLoading(true);
    try {
      let offset = append ? pagination[target].offset : 0;
      const desired = append ? offset + 50 : Math.max(50, pagination[target].offset || (target === initial.view ? initial.loaded || 50 : 50));
      let loaded: GmailReview[] = [];
      let page: ReviewPage;
      do {
        page = await readJson(await fetch(`/api/gmail/reviews?status=${target}&offset=${offset}`));
        if (version !== requestVersion.current) return null;
        loaded = mergeReviews(loaded, page.reviews, target);
        if (page.next_offset <= offset) break;
        offset = page.next_offset;
      } while (!append && page.has_more && (offset < desired || Boolean(ensureId && !loaded.some(item => item.message_id === ensureId))));
      page = { ...page, reviews: loaded };
      if (version !== requestVersion.current) return null;
      setPages(current => ({ ...current, [target]: mergeReviews(append ? current[target] : [], page.reviews, target) }));
      setCounts({ pending: page.pending_count, processed: page.processed_count });
      setPagination(current => ({ ...current, [target]: { hasMore: page.has_more, offset: page.next_offset } }));
      setApplications(page.applications);
      if (!append) setSelectedId(current => loaded.some(item => item.message_id === current) ? current : loaded[0]?.message_id || null);
      setChoices(current => {
        const next = { ...current };
        page.reviews.forEach(item => {
          if (!next[item.message_id]) next[item.message_id] = {
            applicationId: item.candidate_application_ids.length === 1 ? item.candidate_application_ids[0] : '',
            stage: item.proposed_stage || '', dueDate: '', outcome: item.event_code === 'rejected' ? 'rejected' : '', editing: false,
          };
        });
        return next;
      });
      return page;
    } finally { if (version === requestVersion.current) setReviewsLoading(false); }
  }
  async function refresh(target: ReviewView = view) {
    const status = await readJson(await fetch('/api/gmail/status'));
    setConnected(Boolean(status.connected)); setConfigured(Boolean(status.configured)); setReconnect(Boolean(status.reconnect_required));
    if (!status.connected) saveScan(null);
    return loadReviews(target, false, target === view ? selectedId : null);
  }
  useEffect(() => {
    void refresh(initial.view).catch(error => setMessage(error instanceof Error ? error.message : 'Could not load email updates')).finally(() => setLoading(false));
    return () => { requestVersion.current++; };
  }, []);

  function choose(item: GmailReview) {
    setSelectedId(item.message_id); setChangingApplication(false); setQuery('');
  }
  function updateChoice(update: Partial<ReviewChoice>) {
    if (selected && choice) setChoices(current => ({ ...current, [selected.message_id]: { ...choice, ...update } }));
  }
  async function changeView(target: ReviewView) {
    setView(target); setSelectedId(null); setChangingApplication(false); setQuery('');
    try { await loadReviews(target); } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not load reviews'); }
  }
  async function resolve(action: 'link' | 'progress' | 'dismiss') {
    if (!selected || locked) return;
    const item = selected;
    setReviewBusy(item.message_id); setMessage('');
    let committed = false;
    try {
      const result = await readJson(await fetch(`/api/gmail/reviews/${encodeURIComponent(item.message_id)}/resolve`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, application_id: action === 'dismiss' ? null : choice?.applicationId,
          to_stage: action === 'progress' ? choice?.stage : null, due_date: action === 'progress' && datedStages.includes(choice?.stage || '') ? choice?.dueDate || null : null,
          outcome: action === 'progress' && choice?.stage === 'closed' ? choice.outcome || null : null }),
      }));
      committed = true;
      const nextId = nextReviewId(pages.pending, item.message_id);
      setLastUndo(item); setSelectedId(nextId); setChangingApplication(false); setQuery('');
      setPages(current => ({ ...current, pending: current.pending.filter(row => row.message_id !== item.message_id) }));
      setCounts(current => ({ pending: Math.max(0, current.pending - 1), processed: current.processed + 1 }));
      setMessage(action === 'link' ? 'Email link saved. Application stage unchanged.' : action === 'dismiss' ? 'Email dismissed. Application stage unchanged.' : result.stage_changed ? 'Application progress recorded.' : 'Review recorded. Current stage preserved.');
      await Promise.all([loadReviews('pending', false, nextId), action !== 'dismiss' ? onApplicationsChanged() : Promise.resolve()]);
    } catch (error) {
      setMessage(committed ? 'Your decision was saved, but the view could not refresh. Refresh the list before continuing.' : error instanceof Error ? error.message : 'Could not save review');
    } finally { setReviewBusy(''); }
  }
  async function undo(item: GmailReview) {
    if (locked) return;
    setReviewBusy(item.message_id); setMessage('');
    let committed = false;
    try {
      await readJson(await fetch(`/api/gmail/reviews/${encodeURIComponent(item.message_id)}/undo`, { method: 'POST' }));
      committed = true;
      setLastUndo(null); setView('pending'); setSelectedId(item.message_id); setChangingApplication(false);
      const restored = { ...item, status: 'pending', resolved_at: null, can_undo: false };
      setPages(current => ({ pending: mergeReviews(current.pending, [restored], 'pending'), processed: current.processed.filter(row => row.message_id !== item.message_id) }));
      setCounts(current => ({ pending: current.pending + 1, processed: Math.max(0, current.processed - 1) }));
      const [page] = await Promise.all([loadReviews('pending', false, item.message_id), onApplicationsChanged()]);
      if (page && !page.reviews.some(row => row.message_id === item.message_id)) setPages(current => ({ ...current, pending: mergeReviews(current.pending, [restored], 'pending') }));
      setSelectedId(item.message_id);
      setMessage('Decision undone. The email is back in the review queue.');
    } catch (error) { setMessage(committed ? 'Undo was saved, but the view could not refresh. Refresh the list.' : error instanceof Error ? error.message : 'Could not undo this decision'); }
    finally { setReviewBusy(''); }
  }
  async function scan(mode: 'latest' | 'older') {
    if (locked) return;
    const continuing = mode === 'older';
    if (continuing && (!scanProgress || !scanProgressFresh(scanProgress))) {
      saveScan(null); setMessage('The saved scan has expired. Check latest emails to start a new scan.'); return;
    }
    setScanBusy(mode); setMessage('');
    try {
      const result: ScanBatch = await readJson(await fetch('/api/gmail/scan', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recent_days: days, limit, page_token: continuing ? scanProgress?.nextPage : null, window_start: continuing ? scanProgress?.windowStart : null }),
      }));
      setLastBatch(result); setCheckedAt(new Date().toISOString());
      if (continuing || !scanProgress?.nextPage || !scanProgressFresh(scanProgress)) saveScan(advanceScanProgress(continuing ? scanProgress : null, days, limit, result));
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Gmail scan failed');
      if (continuing && error instanceof Error && error.message.includes('start a new scan')) saveScan(null);
      await refresh().catch(() => undefined);
    } finally { setScanBusy(''); }
  }

  function rowHeading(item: GmailReview) {
    const ids = view === 'processed' && item.application_id ? [item.application_id] : item.candidate_application_ids;
    return [...new Set(ids.map(id => applications.find(app => app.id === id)?.company).filter(Boolean))].join(' / ') || 'Application match needed';
  }
  const searchResults = selected ? applicationChoices(applications, selected.candidate_application_ids, query).slice(0, 20) : [];
  const progressValid = Boolean(choice?.stage) && (!datedStages.includes(choice?.stage || '') || Boolean(choice?.dueDate)) && (choice?.stage !== 'closed' || Boolean(choice?.outcome));

  return <section aria-label="Gmail application updates" className="min-w-0 overflow-hidden rounded-2xl border border-ui-line-soft bg-ui-panel/70">
    <header className="space-y-4 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3"><Mail className="mt-1 h-5 w-5 shrink-0 text-ui-ink-amber-400" /><div>
          <h3 className="font-semibold text-ui-heading">Gmail application updates</h3>
          <p className="mt-1 text-xs text-ui-muted">{loading ? 'Checking connection…' : reconnect ? 'Reconnect Gmail to resume scanning' : connected ? 'Gmail connected' : configured ? 'Gmail not connected' : 'Gmail setup needed'}{checkedAt && ` · Checked ${formatDateTime(checkedAt, settings.timezone)}`}</p>
        </div></div>
        <button onClick={() => void scan('latest')} disabled={locked || !connected || !validRange} className={primaryClass}>{scanBusy === 'latest' ? 'Checking latest…' : 'Check latest emails'}</button>
      </div>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-ui-muted">
        {hasOlder && <button onClick={() => void scan('older')} disabled={locked || !connected} className={textButton}>{scanBusy === 'older' ? 'Reading older emails…' : 'Continue older emails'} <ChevronRight className="inline h-3 w-3" /></button>}
        <span>Last {days} days · Up to {limit} messages per batch</span>
        <button onClick={onOpenSettings} disabled={Boolean(reviewBusy)} className="inline-flex items-center gap-1 hover:text-ui-heading disabled:opacity-50">Connection settings <ArrowUpRight className="h-3 w-3" /></button>
      </div>
      <details className="text-xs text-ui-muted"><summary className="cursor-pointer hover:text-ui-heading">Scan options and results</summary>
        <fieldset disabled={locked || hasOlder} className="mt-3 flex flex-wrap gap-3 disabled:opacity-50">
          <label>Recent days<input aria-label="Recent days" type="number" min="1" max="30" step="1" value={days} onChange={e => setDays(Number(e.target.value))} className="ml-2 w-20 rounded border border-ui-line bg-ui-page px-2 py-2 text-ui-heading" /></label>
          <label>Messages per batch<input aria-label="Messages per batch" type="number" min="100" max="200" step="1" value={limit} onChange={e => setLimit(Number(e.target.value))} className="ml-2 w-20 rounded border border-ui-line bg-ui-page px-2 py-2 text-ui-heading" /></label>
        </fieldset>
        {hasOlder && <div className="mt-3 flex flex-wrap items-center gap-3"><span>Older scan: {scanProgress?.batches} batches completed. Position saved in this tab for up to 24 hours.</span><button disabled={locked} onClick={() => saveScan(null)} className={textButton}>Clear position to change options</button></div>}
        {lastBatch && <p className="mt-3" role="status">Latest batch: {lastBatch.scanned} newly checked · {lastBatch.skipped} previously checked · {lastBatch.needs_review} added for review · {lastBatch.ignored_job_board} job alerts filtered.</p>}
        <p className="mt-2">Previously recorded emails are skipped. Gmail stays read-only.</p>
      </details>
      {!loading && !connected && <p className="text-sm text-ui-body">{reconnect ? 'Authorization is no longer valid. Reconnect in Settings.' : 'Connect Gmail in Settings to check for updates.'}</p>}
    </header>
    {(message || lastUndo) && <div role="status" className="flex flex-wrap items-center justify-between gap-3 border-t border-ui-line-soft bg-ui-page/50 px-5 py-3 text-sm text-ui-secondary"><span>{message}</span>{lastUndo && <button onClick={() => void undo(lastUndo)} disabled={locked} className={`inline-flex items-center gap-1 ${textButton}`}><Undo2 className="h-3.5 w-3.5" /> Undo last decision</button>}</div>}
    <div className="flex flex-wrap items-center justify-between gap-3 border-y border-ui-line-soft px-5 py-3">
      <nav aria-label="Email review status" className="flex gap-5">{(['pending', 'processed'] as const).map(target => <button key={target} aria-pressed={view === target} disabled={locked} onClick={() => void changeView(target)} className={`py-1 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-ui-ink-amber-400 disabled:opacity-50 ${view === target ? 'font-semibold text-ui-heading' : 'text-ui-muted hover:text-ui-heading'}`}>{target === 'pending' ? 'Needs review' : 'Processed'} <span className="ml-1 tabular-nums">{counts[target]}</span></button>)}</nav>
      <button disabled={locked} onClick={() => void refresh().catch(error => setMessage(error instanceof Error ? error.message : 'Could not refresh'))} className="text-xs text-ui-muted hover:text-ui-heading disabled:opacity-50">Refresh list</button>
    </div>
    {loading ? <div className="grid gap-3 p-5 sm:grid-cols-3" aria-label="Loading email reviews">{[0, 1, 2].map(key => <div key={key} className="h-24 animate-pulse rounded-lg bg-ui-raised/50" />)}</div> : !rows.length ? <div className="px-5 py-10 text-center"><Check className="mx-auto mb-3 h-6 w-6 text-ui-muted" /><p className="font-medium text-ui-heading">{view === 'pending' ? 'No emails waiting for review' : 'No processed emails yet'}</p><p className="mt-2 text-sm text-ui-muted">{view === 'pending' ? 'Check latest emails whenever you want to look for new updates.' : 'Saved links and dismissed emails will appear here.'}</p></div> : <div className="grid min-w-0 lg:grid-cols-[minmax(15rem,0.85fr)_minmax(0,1.65fr)]" aria-busy={Boolean(reviewBusy) || reviewsLoading}>
      <aside ref={queueRef} aria-label="Email review queue" className="max-h-64 min-w-0 overflow-y-auto border-b border-ui-line-soft p-2 lg:max-h-[38rem] lg:border-b-0 lg:border-r">
        <p className="px-3 py-2 text-xs text-ui-muted">{view === 'pending' ? 'Newest emails first' : 'Most recently processed first'}</p>
        <ul className="space-y-1">{rows.map(item => <li key={item.message_id}><button onClick={() => choose(item)} disabled={locked} aria-pressed={selected?.message_id === item.message_id} className={`w-full min-w-0 rounded-lg px-3 py-3 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-ui-ink-amber-400 disabled:opacity-60 ${selected?.message_id === item.message_id ? 'bg-ui-fill-amber-900/20 text-ui-heading' : 'text-ui-body hover:bg-ui-raised/60'}`}>
          <span className="block break-words text-sm font-semibold">{rowHeading(item)}</span>
          <span className="mt-1 block text-sm">{eventLabels[item.event_code] || 'Related message'}</span>
          <span className="mt-1 block text-xs leading-relaxed text-ui-muted">{formatDateTime(item.received_at, settings.timezone)}</span>
          <span className="mt-1 block text-xs text-ui-muted">{view === 'pending' ? shortReasons[item.reason_code] || 'Check original email' : statusLabels[item.status] || 'Processed'}</span>
        </button></li>)}</ul>
        {pagination[view].hasMore && <button disabled={locked} onClick={() => void loadReviews(view, true).catch(error => setMessage(error instanceof Error ? error.message : 'Could not load more'))} className={`m-2 ${buttonClass}`}>Load more emails</button>}
      </aside>
      {selected && <article aria-label="Selected email review" className="min-w-0 space-y-5 p-5 sm:p-6">
        <div><p className="text-xs text-ui-muted">{formatDateTime(selected.received_at, settings.timezone)}</p><h4 className="mt-2 text-lg font-semibold text-ui-heading">{eventLabels[selected.event_code] || 'Related message'}</h4><a href={originalUrl(selected)} target="_blank" rel="noopener noreferrer" className={`mt-2 inline-flex items-center gap-1 ${textButton}`}>Open original email in Gmail <ArrowUpRight className="h-3.5 w-3.5" /></a></div>
        <GmailMessagePreview key={selected.message_id} messageId={selected.message_id} connected={connected} />
        <div className="border-t border-ui-line-soft pt-5"><p className="text-xs text-ui-muted">{view === 'pending' ? 'Application to link' : 'Application'}</p>
          {selectedApplication ? <><p className="mt-2 break-words font-semibold text-ui-heading">{selectedApplication.company}</p><p className="mt-1 break-words text-sm text-ui-body">{selectedApplication.title}</p></> : <p className="mt-2 text-sm text-ui-body">{view === 'pending' ? 'Choose the application this email concerns.' : 'No application link saved.'}</p>}
          {view === 'pending' && <button disabled={locked} onClick={() => { setChangingApplication(!changingApplication); setQuery(''); }} className={`mt-2 ${textButton}`}>{selectedApplication ? 'Change application' : 'Choose application'}</button>}
          {view === 'pending' && (changingApplication || !selectedApplication) && <div className="mt-3 space-y-2"><label className="flex items-center gap-2 rounded-lg border border-ui-line bg-ui-page px-3 py-2"><Search className="h-4 w-4 shrink-0 text-ui-muted" /><input aria-label="Find application" disabled={locked} value={query} onChange={e => setQuery(e.target.value)} placeholder="Search company or role" className="min-w-0 flex-1 bg-transparent text-sm text-ui-heading outline-none" /></label><ul className="space-y-1">{searchResults.map(app => <li key={app.id}><button disabled={locked} onClick={() => { updateChoice({ applicationId: app.id }); setChangingApplication(false); }} className="w-full rounded px-2 py-2 text-left text-sm text-ui-body hover:bg-ui-raised disabled:opacity-50"><span className="block font-medium">{app.company}{selected.candidate_application_ids.includes(app.id) ? ' · Possible match' : ''}</span><span className="block break-words text-xs text-ui-muted">{app.title} · {stageLabel(app.current_stage)}</span></button></li>)}</ul>{!searchResults.length && <p className="text-sm text-ui-muted">No applications match this search.</p>}</div>}
          {view === 'pending' && <p className="mt-3 text-sm leading-relaxed text-ui-muted">{reasonLabels[selected.reason_code] || 'Check the original before confirming this application link.'}</p>}
        </div>
        {selectedApplication && <div className="border-t border-ui-line-soft pt-5"><p className="text-xs text-ui-muted">Current application stage</p><p className="mt-2 font-medium capitalize text-ui-heading">{stageLabel(selectedApplication.current_stage)}</p><p className="mt-2 text-sm text-ui-muted">Saving an email link keeps this stage unchanged.</p></div>}
        {view === 'pending' && choice && <div className="space-y-4 border-t border-ui-line-soft pt-5">
          <div className="flex flex-wrap gap-3"><button disabled={locked || !selectedApplication} onClick={() => void resolve('link')} className={primaryClass}>Save link &amp; next <ChevronRight className="h-4 w-4" /></button><button disabled={locked || !selectedApplication} onClick={() => updateChoice({ editing: !choice.editing })} aria-expanded={choice.editing} className={buttonClass}>Update progress</button><button disabled={locked} onClick={() => void resolve('dismiss')} className={textButton}>Dismiss email</button></div>
          {choice.editing && <form onSubmit={e => { e.preventDefault(); void resolve('progress'); }} className="space-y-4 rounded-lg bg-ui-page/60 p-4"><p className="text-sm font-medium text-ui-heading">Confirm progress supported by this email</p><label className="block text-xs text-ui-muted">Confirmed stage<select aria-label="Confirmed stage" disabled={locked} value={choice.stage} onChange={e => updateChoice({ stage: e.target.value })} className="mt-1 block w-full rounded border border-ui-line bg-ui-panel px-3 py-2 text-sm text-ui-heading"><option value="">Choose confirmed stage</option>{stages.map(stage => <option key={stage} value={stage}>{stageLabel(stage)}</option>)}</select></label>
            {datedStages.includes(choice.stage) && <label className="block text-xs text-ui-muted">{choice.stage === 'assessment' ? 'Confirmed deadline' : 'Confirmed interview date'}<input aria-label="Confirmed date" disabled={locked} type="date" min={calendarDay(selected.received_at, settings.timezone) || undefined} value={choice.dueDate} onChange={e => updateChoice({ dueDate: e.target.value })} className="mt-1 block max-w-full rounded border border-ui-line bg-ui-panel px-3 py-2 text-sm text-ui-heading" /></label>}
            {choice.stage === 'closed' && <label className="block text-xs text-ui-muted">Confirmed outcome<select aria-label="Confirmed outcome" disabled={locked} value={choice.outcome} onChange={e => updateChoice({ outcome: e.target.value })} className="mt-1 block w-full rounded border border-ui-line bg-ui-panel px-3 py-2 text-sm text-ui-heading"><option value="">Choose outcome</option><option value="rejected">Rejected</option><option value="withdrawn">Withdrawn</option><option value="offer_accepted">Offer accepted</option><option value="offer_declined">Offer declined</option></select></label>}
            <p className="text-xs leading-relaxed text-ui-muted">Received {formatDate(selected.received_at, settings.timezone)}. Older emails cannot overwrite later confirmed progress.</p><button disabled={locked || !selectedApplication || !progressValid} type="submit" className={primaryClass}>Confirm progress &amp; next</button>
          </form>}
        </div>}
        {view === 'processed' && <div className="space-y-3 border-t border-ui-line-soft pt-5"><p className="text-sm font-medium text-ui-heading">{statusLabels[selected.status] || 'Processed'}{selected.resolved_at && <span className="mt-1 block text-xs font-normal text-ui-muted">{formatDateTime(selected.resolved_at, settings.timezone)}</span>}</p>{selected.can_undo ? <button disabled={locked} onClick={() => void undo(selected)} className={`inline-flex items-center gap-2 ${buttonClass}`}><Undo2 className="h-4 w-4" /> Undo decision</button> : <p className="text-xs text-ui-muted">This older decision has no automatic undo record.</p>}</div>}
      </article>}
    </div>}
  </section>;
};
