export type GmailMessagePreview = { message_id: string; subject: string; body: string; truncated: boolean };

export async function loadMessagePreview(messageId: string, signal: AbortSignal, fetcher: typeof fetch = fetch): Promise<GmailMessagePreview> {
  const fallback = 'Could not load email preview. Try again or open the original in Gmail.';
  const response = await fetcher(`/api/gmail/reviews/${encodeURIComponent(messageId)}/preview`, { cache: 'no-store', signal });
  if (!response.headers.get('content-type')?.includes('application/json')) throw new Error(fallback);
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : fallback);
  if (result.message_id !== messageId || typeof result.subject !== 'string' || typeof result.body !== 'string' || typeof result.truncated !== 'boolean') throw new Error(fallback);
  return { message_id: messageId, subject: result.subject, body: result.body, truncated: result.truncated };
}
