import React, { useEffect, useState } from 'react';
import { useTimeSettings } from '../timeSettings';
import { formatDateTime } from '../time';
import { AppearanceSettings } from './AppearanceSettings';
import { writeScanProgress } from '../gmailScanProgress';

type Provider = 'gemini' | 'codex';
type Settings = { provider: Provider; model: string; configured: boolean };
const defaults: Record<Provider, string> = { gemini: 'gemini-3.5-flash-lite', codex: '' };

const readJson = async (response: Response) => {
  if (!response.headers.get('content-type')?.includes('application/json')) {
    throw new Error(`Server error (${response.status}). Check the DoorKnock backend log.`);
  }
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || `Request failed (${response.status})`);
  return result;
};

export const SettingsView: React.FC = () => {
  const { settings: timeSettings, setTimezone } = useTimeSettings();
  const [selectedTimezone, setSelectedTimezone] = useState(timeSettings.timezone);
  const [timeBusy, setTimeBusy] = useState(false);
  const [timeMessage, setTimeMessage] = useState('');
  const [previewInstant, setPreviewInstant] = useState(new Date().toISOString());
  useEffect(() => {
    const timer = window.setInterval(() => setPreviewInstant(new Date().toISOString()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const saveTimezone = async () => {
    setTimeBusy(true);
    setTimeMessage('');
    try {
      const result = await readJson(await fetch('/api/settings/time', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ timezone: selectedTimezone }),
      }));
      setTimezone(result.timezone);
      setSelectedTimezone(result.timezone);
      setTimeMessage('Time zone saved. Dates and new documents now use this time zone.');
    } catch (error) {
      setTimeMessage(error instanceof Error ? error.message : 'Could not save time zone');
    } finally { setTimeBusy(false); }
  };
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
  const [gmailReconnectRequired, setGmailReconnectRequired] = useState(false);
  const [gmailBusy, setGmailBusy] = useState(false);
  const [gmailMessage, setGmailMessage] = useState('');
  const refreshGmail = async () => {
    const status = await readJson(await fetch('/api/gmail/status'));
    setGmailConfigured(Boolean(status.configured));
    setGmailConnected(Boolean(status.connected));
    setGmailReconnectRequired(Boolean(status.reconnect_required));
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
      try { writeScanProgress(window.sessionStorage, null); } catch { /* Storage can be disabled. */ }
      window.open(result.auth_url, '_blank', 'noopener,noreferrer');
      setGmailMessage('Complete Google sign-in, then click Check connection.');
    } catch (error) {
      setGmailMessage(error instanceof Error ? error.message : 'Could not connect Gmail');
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
        <h2 className="text-2xl font-semibold text-ui-heading">Settings</h2>
        <p className="text-sm text-ui-muted mt-2">Manage appearance, your time zone, Gmail connection, AI, and resume formatting.</p>
      </div>
      <AppearanceSettings />
      <div className="rounded-xl border border-ui-line-soft bg-ui-panel p-6 space-y-5">
        <div>
          <h3 className="text-lg font-semibold text-ui-heading">Time zone</h3>
          <p className="text-sm text-ui-muted mt-1">Use the same time zone for dates, follow-ups, and new documents. Daylight saving time adjusts automatically.</p>
        </div>
        <label className="block text-sm text-ui-secondary" htmlFor="timezone">Time zone</label>
        <select id="timezone" value={selectedTimezone} disabled={timeBusy}
          onChange={event => { setSelectedTimezone(event.target.value); setTimeMessage(''); }}
          className="w-full rounded-lg border border-ui-line bg-ui-page px-3 py-2 text-ui-heading">
          {timeSettings.available_timezones.map(zone => <option key={zone} value={zone}>{zone.replaceAll('_', ' ')}</option>)}
        </select>
        <p className="text-sm text-ui-body">Current time: <span className="font-medium text-ui-heading">{formatDateTime(previewInstant, selectedTimezone)}</span></p>
        <p className="text-xs text-ui-muted">Saved time zone: {timeSettings.timezone}. Existing application dates and published documents keep their original dates. Older times without a recorded time zone are shown as entered.</p>
        <div className="flex flex-wrap gap-3">
          <button disabled={timeBusy} onClick={() => {
            const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            if (timeSettings.available_timezones.includes(zone)) {
              setSelectedTimezone(zone);
              setTimeMessage('Device time zone selected. Click Save time zone to apply.');
            } else { setTimeMessage('Select your time zone from the list.'); }
          }} className="rounded-lg border border-ui-line px-4 py-2 text-sm text-ui-secondary hover:bg-ui-raised disabled:opacity-50">Use device time zone</button>
          <button onClick={() => void saveTimezone()} disabled={timeBusy}
            className="rounded-lg bg-ui-fill-amber-600 px-4 py-2 text-sm font-semibold text-ui-on-action hover:bg-ui-fill-amber-500 disabled:opacity-50">{timeBusy ? 'Saving…' : 'Save time zone'}</button>
        </div>
        {timeMessage && <p role="status" className="text-sm text-ui-secondary">{timeMessage}</p>}
      </div>
      <div className="rounded-xl border border-ui-line-soft bg-ui-panel p-6 space-y-5">
        <div>
          <h3 className="text-lg font-semibold text-ui-heading">Gmail connection</h3>
          <p className="text-sm text-ui-muted mt-1">Connect your Gmail account to find messages about jobs already saved in DoorKnock.</p>
        </div>
        <ol className="space-y-3 text-sm text-ui-secondary list-decimal list-inside">
          <li><span className="font-medium">Set up Gmail once.</span> DoorKnock needs a one-time Google setup before anyone can connect. If you did not install DoorKnock yourself, ask the person who did to complete the setup below.</li>
          <li><span className="font-medium">Connect your account.</span> Click Connect Gmail, sign in to Google, allow read-only access, then return here and click Check connection.</li>
        </ol>
        <p className="text-sm text-ui-body">Scan application updates and review matches on the <a href="#dashboard" className="text-ui-ink-amber-400 underline">Dashboard</a>.</p>
        <p className="text-sm text-ui-body">Setup: <span className={gmailConfigured ? 'text-ui-ink-emerald-400' : 'text-ui-ink-amber-400'}>{gmailConfigured ? 'ready' : 'needed'}</span> · Gmail account: <span className={gmailConnected ? 'text-ui-ink-emerald-400' : 'text-ui-ink-amber-400'}>{gmailReconnectRequired ? 'reconnect required' : gmailConnected ? 'connected' : 'not connected'}</span></p>
        {gmailReconnectRequired && <p className="text-sm text-ui-body">Gmail authorization is no longer valid. Reconnect your account to resume scanning.</p>}
        <details className="rounded-lg border border-ui-line bg-ui-page/70 p-4 text-sm text-ui-body">
          <summary className="cursor-pointer font-medium text-ui-primary">One-time Google setup instructions</summary>
          <ol className="mt-3 space-y-2 list-decimal list-inside">
            <li>In Google Cloud, enable the Gmail API and create an OAuth client of type <strong>Web application</strong>.</li>
            <li>Add <code className="text-ui-ink-amber-300">http://localhost:8000/api/gmail/callback</code> as an authorized redirect URI.</li>
            <li>Put the client ID and client secret in DoorKnock's local <code className="text-ui-ink-amber-300">.env</code> file as <code className="text-ui-ink-amber-300">GMAIL_CLIENT_ID</code> and <code className="text-ui-ink-amber-300">GMAIL_CLIENT_SECRET</code>, then restart DoorKnock.</li>
            <li>If Google's consent screen is in testing mode, add the Gmail account as a test user.</li>
          </ol>
          <p className="mt-3 text-xs text-ui-muted">These credentials stay on this computer. DoorKnock requests read-only Gmail access and saves references to matched messages, not email text or attachments.</p>
        </details>
        <div className="flex flex-wrap gap-3">
          <button onClick={connectGmail} disabled={gmailBusy || !gmailConfigured} className="rounded-lg border border-ui-line-strong px-4 py-2 text-sm text-ui-heading disabled:opacity-50">{gmailReconnectRequired ? 'Reconnect Gmail' : 'Connect Gmail'}</button>
          <button onClick={() => void refreshGmail().catch(error => setGmailMessage(String(error)))} disabled={gmailBusy} className="rounded-lg border border-ui-line-strong px-4 py-2 text-sm text-ui-heading disabled:opacity-50">Check connection</button>
        </div>
        {!gmailConfigured && <p className="text-xs text-ui-muted">Connect Gmail becomes available after the one-time setup.</p>}
        {gmailMessage && <p role="status" className="text-sm text-ui-secondary">{gmailMessage}</p>}
      </div>
      <div className="rounded-xl border border-ui-line-soft bg-ui-panel p-6 space-y-5">
        <h3 className="text-lg font-semibold text-ui-heading">AI provider</h3>
        <label className="block text-sm font-medium text-ui-secondary" htmlFor="ai-provider">Provider</label>
        <select id="ai-provider" value={provider} onChange={event => {
          const next = event.target.value as Provider;
          setProvider(next);
          setModel(defaults[next]);
          setConfigured(false);
          setMessage('');
        }} className="w-full rounded-lg border border-ui-line bg-ui-page px-3 py-2 text-ui-heading">
          <option value="gemini">Google Gemini</option>
          <option value="codex">Codex (ChatGPT sign-in)</option>
        </select>
        <label className="block text-sm font-medium text-ui-secondary" htmlFor="ai-model">Model ID</label>
        <input id="ai-model" value={model} onChange={event => setModel(event.target.value)}
          placeholder={provider === 'codex' ? 'Leave blank to use Codex default' : undefined}
          className="w-full rounded-lg border border-ui-line bg-ui-page px-3 py-2 text-ui-heading" />
        {provider === 'codex' && (
          <p className="text-xs text-ui-subtle">
            Leave blank to use the model selected by Codex.{' '}
            <a href="https://learn.chatgpt.com/docs/models?surface=app" target="_blank" rel="noopener noreferrer" className="text-ui-ink-amber-400 underline hover:text-ui-ink-amber-300">
              View Codex model IDs
            </a>
          </p>
        )}
        {provider === 'gemini' ? (
          <p className="text-sm text-ui-muted">Server credential: <span className={configured ? 'text-ui-ink-emerald-400' : 'text-ui-ink-amber-400'}>{configured ? 'configured' : 'not configured'}</span>. Set GEMINI_API_KEY in the server environment or local .env file.</p>
        ) : (
          <div className="space-y-3 text-sm text-ui-muted">
            <p>Codex CLI: <span className={configured ? 'text-ui-ink-emerald-400' : 'text-ui-ink-amber-400'}>{configured ? 'available' : 'not found on the server PATH'}</span></p>
            <p>ChatGPT connection: <span className={codexConnected ? 'text-ui-ink-emerald-400' : 'text-ui-ink-amber-400'}>{codexConnected ? 'connected' : 'not connected'}</span></p>
            <div className="flex gap-3">
              <button onClick={connectCodex} disabled={busy || !configured || codexConnected} className="rounded-lg border border-ui-line-strong px-4 py-2 text-ui-heading hover:bg-ui-raised disabled:opacity-50">{codexConnected ? 'Codex connected' : 'Connect Codex'}</button>
              <button onClick={() => void checkCodex()} className="rounded-lg border border-ui-line px-4 py-2 text-ui-secondary hover:bg-ui-raised">Check status</button>
            </div>
            {authUrl && !codexConnected && <a href={authUrl} target="_blank" rel="noreferrer" className="text-ui-ink-amber-400 underline">Open ChatGPT sign-in</a>}
          </div>
        )}
        <button onClick={save} disabled={busy || (provider === 'gemini' && !model.trim())} className="rounded-lg bg-ui-fill-amber-600 px-4 py-2 text-sm font-semibold text-ui-on-action hover:bg-ui-fill-amber-500 disabled:opacity-50">{busy ? 'Saving…' : 'Save settings'}</button>
        {message && <p role="status" className="text-sm text-ui-secondary">{message}</p>}
      </div>
      <div className="rounded-xl border border-ui-line-soft bg-ui-panel p-6 space-y-5">
        <div>
          <h3 className="text-lg font-semibold text-ui-heading">Resume formatting</h3>
          <p className="text-sm text-ui-muted mt-1">The first resume (v001) can use multiple pages. Choose the page limit for later versions.</p>
        </div>
        <label className="flex items-start gap-3 text-sm text-ui-secondary">
          <input
            type="checkbox"
            checked={requireSinglePageResume}
            disabled={resumeSettingsLoading}
            onChange={event => setRequireSinglePageResume(event.target.checked)}
            className="mt-1 accent-ui-ink-amber-500"
          />
          <span>
            Require later resume versions to fit on one page
            <span className="block text-xs text-ui-muted mt-1">
              Off by default. When off, multi-page resumes are allowed and still checked for valid PDF content.
            </span>
          </span>
        </label>
        <button onClick={saveResumeSettings} disabled={resumeSettingsBusy || resumeSettingsLoading}
          className="rounded-lg bg-ui-fill-amber-600 px-4 py-2 text-sm font-semibold text-ui-on-action hover:bg-ui-fill-amber-500 disabled:opacity-50">
          {resumeSettingsLoading ? 'Loading…' : resumeSettingsBusy ? 'Saving…' : 'Save resume settings'}
        </button>
        {resumeSettingsMessage && <p role="status" className="text-sm text-ui-secondary">{resumeSettingsMessage}</p>}
      </div>
      <p className="text-sm text-ui-subtle">Codex manages its own ChatGPT sign-in. DoorKnock stores your time zone, provider, model, and resume formatting preferences locally.</p>
    </section>
  );
};
