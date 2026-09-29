import React, { useEffect, useState } from 'react';

type Provider = 'gemini' | 'codex';
type Settings = { provider: Provider; model: string; configured: boolean };
type GmailReview = { message_id: string; received_at: string; event_code: string; proposed_stage: string | null; reason_code: string; candidate_application_ids: string[] };
type GmailApplication = { id: string; company: string; title: string; current_stage: string };
type ReviewChoice = { applicationId: string; stage: string };
const defaults: Record<Provider, string> = { gemini: 'gemini-3.5-flash-lite', codex: '' };
const gmailEventLabels: Record<string, string> = {
  application_received: 'Application received',
  recruiter_screen_scheduled: 'Recruiter screen scheduled',
  rejected: 'Application declined',
  related: 'Related message',
};
const gmailReviewReasons: Record<string, string> = {
  multiple_applications: 'More than one application could match',
  no_application_match: 'No application matched clearly',
  unclear_event: 'The message does not clearly confirm a stage',
  bulk_or_automated: 'Automated or bulk message; check it before changing a stage',
  older_message: 'Message predates the recorded application',
  stage_conflict: 'Suggested change conflicts with the current stage',
};
const reviewStages = [
  'applied', 'knocked', 'recruiter_screen', 'assessment', 'team_match',
  'technical_interview', 'final_round', 'offer', 'closed',
];

const readJson = async (response: Response) => {
  if (!response.headers.get('content-type')?.includes('application/json')) {
    throw new Error(`Server error (${response.status}). Check the DoorKnock backend log.`);
  }
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || `Request failed (${response.status})`);
  return result;
};

export const SettingsView: React.FC = () => {
  const [provider, setProvider] = useState<Provider>('gemini');
  const [model, setModel] = useState(defaults.gemini);
  const [configured, setConfigured] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [requireSinglePageResume, setRequireSinglePageResume] = useState(false);
  const [resumeSettingsLoading, setResumeSettingsLoading] = useState(true);
  const [resumeSettingsBusy, setResumeSettingsBusy] = useState(false);
  const [resumeSettingsMessage, setResumeSettingsMessage] = useState('');
  const [codexConnected, setCodexConnected] = useState(false);
  const [authUrl, setAuthUrl] = useState('');
  const [gmailConfigured, setGmailConfigured] = useState(false);
  const [gmailConnected, setGmailConnected] = useState(false);
  const [gmailBusy, setGmailBusy] = useState(false);
  const [gmailMessage, setGmailMessage] = useState('');
  const [gmailLimit, setGmailLimit] = useState(150);
  const [gmailDays, setGmailDays] = useState(14);
  const [gmailMessages, setGmailMessages] = useState<Array<{message_id: string; company: string; title: string; event_code: string; stage_applied: number}>>([]);
  const [gmailNextPage, setGmailNextPage] = useState('');
  const [gmailWindowStart, setGmailWindowStart] = useState<number | null>(null);
  const [gmailReviews, setGmailReviews] = useState<GmailReview[]>([]);
  const [gmailApplications, setGmailApplications] = useState<GmailApplication[]>([]);
  const [reviewChoices, setReviewChoices] = useState<Record<string, ReviewChoice>>({});
  const [reviewBusy, setReviewBusy] = useState('');

  const refreshGmail = async () => {
    const status = await readJson(await fetch('/api/gmail/status'));
    setGmailConfigured(Boolean(status.configured));
    setGmailConnected(Boolean(status.connected));
    const saved = await readJson(await fetch('/api/gmail/messages'));
    setGmailMessages(saved.messages || []);
    const pending = await readJson(await fetch('/api/gmail/reviews'));
    setGmailReviews(pending.reviews || []);
    setGmailApplications(pending.applications || []);
    setReviewChoices(current => {
      const next = { ...current };
      for (const item of pending.reviews || []) {
        if (!next[item.message_id]) {
          next[item.message_id] = {
            applicationId: item.candidate_application_ids.length === 1 ? item.candidate_application_ids[0] : '',
            stage: item.proposed_stage || '',
          };
        }
      }
      return next;
    });
  };

  const resolveGmailReview = async (item: GmailReview, action: 'apply' | 'dismiss') => {
    setReviewBusy(item.message_id);
    setGmailMessage('');
    try {
      const choice = reviewChoices[item.message_id];
      const result = await readJson(await fetch(`/api/gmail/reviews/${encodeURIComponent(item.message_id)}/resolve`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, application_id: choice?.applicationId || null, to_stage: choice?.stage || null }),
      }));
      await refreshGmail();
      setGmailMessage(action === 'dismiss' ? 'Review dismissed. No stage was changed.' : result.stage_changed ? 'Stage updated and recorded in the application timeline.' : 'Review saved. The application was already at that stage.');
    } catch (error) {
      setGmailMessage(error instanceof Error ? error.message : 'Could not save review');
    } finally { setReviewBusy(''); }
  };

  const checkCodex = async () => {
    try {
      const response = await fetch('/api/settings/codex/status');
      const status = await readJson(response);
      setCodexConnected(Boolean(status.connected));
    } catch (error) {
      setCodexConnected(false);
      setMessage(error instanceof Error ? error.message : 'Could not check Codex status');
    }
  };

  useEffect(() => {
    void refreshGmail().catch(error => setGmailMessage(error instanceof Error ? error.message : 'Could not check Gmail'));
    fetch('/api/settings/ai')
      .then(async response => {
        return readJson(response) as Promise<Settings>;
      })
      .then(settings => {
        setProvider(settings.provider);
        setModel(settings.model);
        setConfigured(settings.configured);
      })
      .catch(error => setMessage(String(error)));

    fetch('/api/settings/resume')
      .then(readJson)
      .then(settings => setRequireSinglePageResume(Boolean(settings.require_single_page)))
      .catch(error => setResumeSettingsMessage(error instanceof Error ? error.message : 'Could not load resume settings'))
      .finally(() => setResumeSettingsLoading(false));
  }, []);

  const connectGmail = async () => {
    setGmailBusy(true);
    setGmailMessage('');
    try {
      const result = await readJson(await fetch('/api/gmail/connect', { method: 'POST' }));
      window.open(result.auth_url, '_blank', 'noopener,noreferrer');
      setGmailMessage('Complete Google sign-in, then click Check connection.');
    } catch (error) {
      setGmailMessage(error instanceof Error ? error.message : 'Could not connect Gmail');
    } finally { setGmailBusy(false); }
  };

  const scanGmail = async (nextPage = false) => {
    setGmailBusy(true);
    setGmailMessage('');
    try {
      const result = await readJson(await fetch('/api/gmail/scan', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recent_days: gmailDays, limit: gmailLimit,
          page_token: nextPage ? gmailNextPage : null,
          window_start: nextPage ? gmailWindowStart : null }),
      }));
      setGmailNextPage(result.next_page_token || '');
      setGmailWindowStart(result.window_start || null);
      setGmailMessage(`Checked ${result.scanned} messages; filtered ${result.ignored_job_board || 0} job-board alerts; saved ${result.saved} relevant messages; updated ${result.stage_changed} stages; ${result.needs_review} need review.${result.more_available ? ' More messages matched the date range than this scan covered.' : ''}`);
      await refreshGmail();
    } catch (error) {
      setGmailMessage(error instanceof Error ? error.message : 'Gmail scan failed');
    } finally { setGmailBusy(false); }
  };

  useEffect(() => {
    if (provider !== 'codex') return;
    void checkCodex();
    if (!authUrl) return;
    const timer = window.setInterval(() => void checkCodex(), 2500);
    return () => window.clearInterval(timer);
  }, [provider, authUrl]);

  const connectCodex = async () => {
    setBusy(true);
    setMessage('');
    try {
      const response = await fetch('/api/settings/codex/connect', { method: 'POST' });
      const result = await readJson(response);
      if (!result.auth_url) throw new Error('Codex did not return a sign-in link');
      setAuthUrl(result.auth_url);
      window.open(result.auth_url, '_blank', 'noopener,noreferrer');
      setMessage('Complete ChatGPT sign-in in the browser, then check connection status here.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not connect Codex');
    } finally { setBusy(false); }
  };

  const save = async () => {
    setBusy(true);
    setMessage('');
    try {
      const response = await fetch('/api/settings/ai', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, model }),
      });
      const result = await readJson(response);
      setConfigured(result.configured);
      setMessage('AI settings saved. New requests will use this provider.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not save settings');
    } finally {
      setBusy(false);
    }
  };

  const saveResumeSettings = async () => {
    setResumeSettingsBusy(true);
    setResumeSettingsMessage('');
    try {
      const response = await fetch('/api/settings/resume', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ require_single_page: requireSinglePageResume }),
      });
      const result = await readJson(response);
      setRequireSinglePageResume(Boolean(result.require_single_page));
      setResumeSettingsMessage('Resume settings saved. New resumes will use this preference.');
    } catch (error) {
      setResumeSettingsMessage(error instanceof Error ? error.message : 'Could not save resume settings');
    } finally {
      setResumeSettingsBusy(false);
    }
  };

  return (
    <section className="max-w-3xl mx-auto px-6 py-10 space-y-7">
      <div>
        <h2 className="text-2xl font-semibold text-white">Settings</h2>
        <p className="text-sm text-slate-400 mt-2">Manage Gmail scans, AI, and resume formatting.</p>
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-5">
        <div>
          <h3 className="text-lg font-semibold text-white">Gmail application updates</h3>
          <p className="text-sm text-slate-400 mt-1">Connect your Gmail account to find messages about jobs already saved in DoorKnock.</p>
        </div>
        <ol className="space-y-3 text-sm text-slate-200 list-decimal list-inside">
          <li><span className="font-medium">Set up Gmail once.</span> DoorKnock needs a one-time Google setup before anyone can connect. If you did not install DoorKnock yourself, ask the person who did to complete the setup below.</li>
          <li><span className="font-medium">Connect your account.</span> Click Connect Gmail, sign in to Google, allow read-only access, then return here and click Check connection.</li>
          <li><span className="font-medium">Choose a scan size.</span> Pick how many recent days to check and how many messages to read per scan. The defaults are 14 days and 150 messages.</li>
          <li><span className="font-medium">Scan and review.</span> Click Scan Gmail. Clear messages can update stages. Uncertain ones appear in Needs review, where you can open the original email and decide. If more messages remain, use Scan next page.</li>
        </ol>
        <div className="rounded-lg border border-amber-700/40 bg-amber-950/30 px-4 py-3 text-sm text-amber-100">
          Scanning can change a stage immediately when a message clearly matches one application and confirms an application, recruiter screen, or rejection. Uncertain messages wait for your decision. No emails are sent or changed in Gmail.
        </div>
        <p className="text-xs text-slate-400">Job alerts and recommendation digests from platforms such as LinkedIn, Handshake, and HiringCafe are filtered out. Direct application updates from those platforms can still be checked. Alerts may still count toward the scan size; use Scan next page if more messages are available.</p>
        <p className="text-sm text-slate-300">Setup: <span className={gmailConfigured ? 'text-emerald-400' : 'text-amber-400'}>{gmailConfigured ? 'ready' : 'needed'}</span> · Gmail account: <span className={gmailConnected ? 'text-emerald-400' : 'text-amber-400'}>{gmailConnected ? 'connected' : 'not connected'}</span></p>
        <details className="rounded-lg border border-slate-700 bg-slate-950/70 p-4 text-sm text-slate-300">
          <summary className="cursor-pointer font-medium text-slate-100">One-time Google setup instructions</summary>
          <ol className="mt-3 space-y-2 list-decimal list-inside">
            <li>In Google Cloud, enable the Gmail API and create an OAuth client of type <strong>Web application</strong>.</li>
            <li>Add <code className="text-amber-300">http://localhost:8000/api/gmail/callback</code> as an authorized redirect URI.</li>
            <li>Put the client ID and client secret in DoorKnock's local <code className="text-amber-300">.env</code> file as <code className="text-amber-300">GMAIL_CLIENT_ID</code> and <code className="text-amber-300">GMAIL_CLIENT_SECRET</code>, then restart DoorKnock.</li>
            <li>If Google's consent screen is in testing mode, add the Gmail account as a test user.</li>
          </ol>
          <p className="mt-3 text-xs text-slate-400">These credentials stay on this computer. DoorKnock requests read-only Gmail access and saves references to matched messages, not email text or attachments.</p>
        </details>
        <div className="flex flex-wrap gap-3">
          <button onClick={connectGmail} disabled={gmailBusy || !gmailConfigured} className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-white disabled:opacity-50">Connect Gmail</button>
          <button onClick={() => void refreshGmail().catch(error => setGmailMessage(String(error)))} disabled={gmailBusy} className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-white disabled:opacity-50">Check connection</button>
        </div>
        {!gmailConfigured && <p className="text-xs text-slate-400">Connect Gmail becomes available after the one-time setup.</p>}
        <div className="flex flex-wrap gap-4">
          <label className="text-sm text-slate-200">Recent days (1–30)
            <input type="number" min="1" max="30" value={gmailDays} onChange={event => setGmailDays(Number(event.target.value))} className="ml-2 w-20 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-white" />
          </label>
          <label className="text-sm text-slate-200">Messages per scan (100–200)
            <input type="number" min="100" max="200" value={gmailLimit} onChange={event => setGmailLimit(Number(event.target.value))} className="ml-2 w-20 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-white" />
          </label>
        </div>
        <div className="flex gap-3">
          <button onClick={() => void scanGmail()} disabled={gmailBusy || !gmailConnected || gmailLimit < 100 || gmailLimit > 200 || gmailDays < 1 || gmailDays > 30} className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-500 disabled:opacity-50">{gmailBusy ? 'Working…' : 'Scan Gmail'}</button>
          {gmailNextPage && <button onClick={() => void scanGmail(true)} disabled={gmailBusy} className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-white disabled:opacity-50">Scan next page</button>}
        </div>
        {gmailMessage && <p role="status" className="text-sm text-slate-200">{gmailMessage}</p>}
        {gmailReviews.length > 0 && <div className="space-y-3 rounded-lg border border-amber-700/40 bg-slate-950/60 p-4">
          <h4 className="text-sm font-semibold text-white">Needs review ({gmailReviews.length})</h4>
          <p className="text-xs text-slate-400">Open each message in Gmail to check the details. Choose an application and stage only when the email supports the change.</p>
          {gmailReviews.map(item => {
            const choice = reviewChoices[item.message_id] || { applicationId: '', stage: '' };
            return <div key={item.message_id} className="space-y-2 border-t border-slate-800 pt-3 text-sm text-slate-200">
              <p>{gmailReviewReasons[item.reason_code] || 'Needs a manual check'} · {gmailEventLabels[item.event_code] || 'Related message'} · {new Date(item.received_at).toLocaleDateString()}</p>
              <a className="text-amber-400 underline" href={`https://mail.google.com/mail/u/0/#all/${encodeURIComponent(item.message_id)}`} target="_blank" rel="noopener noreferrer">Open original email in Gmail</a>
              <div className="flex flex-wrap gap-2">
                <label className="text-xs text-slate-400">Application
                  <select aria-label="Application to update" value={choice.applicationId} onChange={event => setReviewChoices(current => ({ ...current, [item.message_id]: { ...choice, applicationId: event.target.value } }))} className="mt-1 block max-w-72 rounded border border-slate-700 bg-slate-900 px-2 py-2 text-sm text-white">
                    <option value="">Choose application</option>
                    {gmailApplications.map(app => <option key={app.id} value={app.id}>{app.company} · {app.title} ({app.current_stage.replaceAll('_', ' ')}){item.candidate_application_ids.includes(app.id) ? ' · possible match' : ''}</option>)}
                  </select>
                </label>
                <label className="text-xs text-slate-400">Stage
                  <select aria-label="Stage to set" value={choice.stage} onChange={event => setReviewChoices(current => ({ ...current, [item.message_id]: { ...choice, stage: event.target.value } }))} className="mt-1 block rounded border border-slate-700 bg-slate-900 px-2 py-2 text-sm text-white">
                    <option value="">Choose stage</option>
                    {reviewStages.map(stage => <option key={stage} value={stage}>{stage.replaceAll('_', ' ')}</option>)}
                  </select>
                </label>
              </div>
              <div className="flex gap-2">
                <button onClick={() => void resolveGmailReview(item, 'apply')} disabled={Boolean(reviewBusy) || !choice.applicationId || !choice.stage} className="rounded bg-amber-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Confirm stage</button>
                <button onClick={() => void resolveGmailReview(item, 'dismiss')} disabled={Boolean(reviewBusy)} className="rounded border border-slate-600 px-3 py-2 text-xs text-slate-200 disabled:opacity-50">Dismiss</button>
              </div>
            </div>;
          })}
        </div>}
        {gmailMessages.length > 0 && <div className="space-y-2"><h4 className="text-sm font-semibold text-white">Recent matches</h4>{gmailMessages.map(item => <p key={item.message_id} className="text-xs text-slate-300">{item.company} · {item.title} · {gmailEventLabels[item.event_code] || 'Related message'} · {item.stage_applied ? 'Stage updated' : 'Saved for reference'} · <a className="text-amber-400 underline" href={`https://mail.google.com/mail/u/0/#all/${encodeURIComponent(item.message_id)}`} target="_blank" rel="noopener noreferrer">Open in Gmail</a></p>)}</div>}
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-5">
        <h3 className="text-lg font-semibold text-white">AI provider</h3>
        <label className="block text-sm font-medium text-slate-200" htmlFor="ai-provider">Provider</label>
        <select id="ai-provider" value={provider} onChange={event => {
          const next = event.target.value as Provider;
          setProvider(next);
          setModel(defaults[next]);
          setConfigured(false);
          setMessage('');
        }} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white">
          <option value="gemini">Google Gemini</option>
          <option value="codex">Codex (ChatGPT sign-in)</option>
        </select>
        <label className="block text-sm font-medium text-slate-200" htmlFor="ai-model">Model ID</label>
        <input id="ai-model" value={model} onChange={event => setModel(event.target.value)}
          placeholder={provider === 'codex' ? 'Leave blank to use Codex default' : undefined}
          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white" />
        {provider === 'codex' && (
          <p className="text-xs text-slate-500">
            Leave blank to use the model selected by Codex.{' '}
            <a href="https://learn.chatgpt.com/docs/models?surface=app" target="_blank" rel="noopener noreferrer" className="text-amber-400 underline hover:text-amber-300">
              View Codex model IDs
            </a>
          </p>
        )}
        {provider === 'gemini' ? (
          <p className="text-sm text-slate-400">Server credential: <span className={configured ? 'text-emerald-400' : 'text-amber-400'}>{configured ? 'configured' : 'not configured'}</span>. Set GEMINI_API_KEY in the server environment or local .env file.</p>
        ) : (
          <div className="space-y-3 text-sm text-slate-400">
            <p>Codex CLI: <span className={configured ? 'text-emerald-400' : 'text-amber-400'}>{configured ? 'available' : 'not found on the server PATH'}</span></p>
            <p>ChatGPT connection: <span className={codexConnected ? 'text-emerald-400' : 'text-amber-400'}>{codexConnected ? 'connected' : 'not connected'}</span></p>
            <div className="flex gap-3">
              <button onClick={connectCodex} disabled={busy || !configured || codexConnected} className="rounded-lg border border-slate-600 px-4 py-2 text-white hover:bg-slate-800 disabled:opacity-50">{codexConnected ? 'Codex connected' : 'Connect Codex'}</button>
              <button onClick={() => void checkCodex()} className="rounded-lg border border-slate-700 px-4 py-2 text-slate-200 hover:bg-slate-800">Check status</button>
            </div>
            {authUrl && !codexConnected && <a href={authUrl} target="_blank" rel="noreferrer" className="text-amber-400 underline">Open ChatGPT sign-in</a>}
          </div>
        )}
        <button onClick={save} disabled={busy || (provider === 'gemini' && !model.trim())} className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-500 disabled:opacity-50">{busy ? 'Saving…' : 'Save settings'}</button>
        {message && <p role="status" className="text-sm text-slate-200">{message}</p>}
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-5">
        <div>
          <h3 className="text-lg font-semibold text-white">Resume formatting</h3>
          <p className="text-sm text-slate-400 mt-1">Choose whether tailored resumes must fit on one page.</p>
        </div>
        <label className="flex items-start gap-3 text-sm text-slate-200">
          <input
            type="checkbox"
            checked={requireSinglePageResume}
            disabled={resumeSettingsLoading}
            onChange={event => setRequireSinglePageResume(event.target.checked)}
            className="mt-1 accent-amber-500"
          />
          <span>
            Require resumes to fit on one page
            <span className="block text-xs text-slate-400 mt-1">
              Off by default. When off, multi-page resumes are allowed and still checked for valid PDF content.
            </span>
          </span>
        </label>
        <button onClick={saveResumeSettings} disabled={resumeSettingsBusy || resumeSettingsLoading}
          className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-500 disabled:opacity-50">
          {resumeSettingsLoading ? 'Loading…' : resumeSettingsBusy ? 'Saving…' : 'Save resume settings'}
        </button>
        {resumeSettingsMessage && <p role="status" className="text-sm text-slate-200">{resumeSettingsMessage}</p>}
      </div>
      <p className="text-sm text-slate-500">Codex manages its own ChatGPT sign-in. DoorKnock stores provider, model, and resume formatting preferences locally.</p>
    </section>
  );
};
