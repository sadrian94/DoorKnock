import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import ts from 'typescript';
const path = new URL('./gmailMessagePreview.ts', import.meta.url);
const compiled = ts.transpileModule(existsSync(path) ? readFileSync(path, 'utf8') : '', { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { loadMessagePreview } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);

test('preview fetch bypasses cache and uses the selected message and abort signal', async () => {
  const controller = new AbortController();
  const value = { message_id: 'selected', subject: 'Synthetic subject', body: 'Synthetic body', truncated: false };
  const result = await loadMessagePreview('selected', controller.signal, async (url, options) => {
    assert.equal(url, '/api/gmail/reviews/selected/preview');
    assert.equal(options.cache, 'no-store');
    assert.equal(options.signal, controller.signal);
    return new Response(JSON.stringify(value), { headers: { 'content-type': 'application/json' } });
  });
  assert.deepEqual(result, value);
});

test('preview failures show safe errors and reject mismatched message content', async () => {
  const signal = new AbortController().signal;
  await assert.rejects(() => loadMessagePreview('selected', signal, async () => new Response('<html>Private server diagnostic</html>', { status: 502 })), /Could not load email preview/);
  await assert.rejects(() => loadMessagePreview('selected', signal, async () => new Response(JSON.stringify({ detail: 'Reconnect Gmail' }), { status: 400, headers: { 'content-type': 'application/json' } })), /Reconnect Gmail/);
  await assert.rejects(() => loadMessagePreview('selected', signal, async () => new Response(JSON.stringify({ message_id: 'other', subject: 'Wrong subject', body: 'Wrong body', truncated: false }), { headers: { 'content-type': 'application/json' } })), /Could not load email preview/);
});

test('aborted selection requests propagate cancellation', async () => {
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(() => loadMessagePreview('selected', controller.signal, async (_, options) => {
    options.signal.throwIfAborted();
  }), { name: 'AbortError' });
});
