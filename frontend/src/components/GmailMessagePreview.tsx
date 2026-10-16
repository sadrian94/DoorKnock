import { useEffect, useState } from 'react';
import { loadMessagePreview } from '../gmailMessagePreview';
import type { GmailMessagePreview as Preview } from '../gmailMessagePreview';

export function GmailMessagePreview({ messageId, connected }: { messageId: string; connected: boolean }) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(connected);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    setPreview(null); setError(''); setLoading(connected);
    if (!connected) return;
    const controller = new AbortController();
    let active = true;
    void loadMessagePreview(messageId, controller.signal).then(value => {
      if (active) setPreview(value);
    }).catch(reason => {
      if (active) setError(reason instanceof Error ? reason.message : 'Could not load email preview. Try again or open the original in Gmail.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [messageId, connected, attempt]);

  return <section aria-label="Email preview" aria-busy={loading} className="min-w-0 space-y-3 rounded-lg border border-ui-line-soft bg-ui-page/40 p-4">
    <div className="flex flex-wrap items-center justify-between gap-2"><h5 className="text-xs font-medium text-ui-muted">Email preview</h5><span className="text-xs text-ui-muted">Read live · Not saved</span></div>
    {!connected ? <p className="text-sm text-ui-muted">Connect Gmail in Settings to read this email here.</p> : loading ? <p role="status" className="text-sm text-ui-muted">Loading email…</p> : error ? <div className="space-y-2"><p role="alert" className="break-words text-sm text-ui-body">{error}</p><button onClick={() => setAttempt(current => current + 1)} className="text-sm text-ui-ink-amber-400 underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-ui-ink-amber-500">Retry preview</button></div> : preview && <>
      <p className="break-words text-sm font-semibold text-ui-heading">{preview.subject || '(No subject)'}</p>
      <div tabIndex={0} aria-label="Email content" className="max-h-64 overflow-y-auto whitespace-pre-wrap break-words text-sm leading-relaxed text-ui-body focus-visible:outline focus-visible:outline-2 focus-visible:outline-ui-ink-amber-500">{preview.body || 'No text preview is available. Open the original email in Gmail.'}</div>
      {preview.truncated && <p className="text-xs text-ui-muted">Showing the first 20,000 characters. Open the original email in Gmail for the rest.</p>}
    </>}
  </section>;
}
