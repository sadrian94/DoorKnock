import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import ts from 'typescript';

const path = new URL('./gmailScanProgress.ts', import.meta.url);
const source = existsSync(path) ? readFileSync(path, 'utf8') : '';
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { advanceScanProgress, readScanProgress, writeScanProgress } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const start = Date.parse('2026-10-16T12:00:00Z');
const firstBatch = {
  window_start: 1790942400, next_page_token: 'synthetic-page-two',
  scanned: 80, skipped: 70, saved: 4, needs_review: 6, ignored_job_board: 12,
};

function storage() {
  const values = new Map();
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
}

test('refresh restores the next page, date range, batch size and totals', () => {
  const saved = storage();
  const progress = advanceScanProgress(null, 14, 150, firstBatch);
  writeScanProgress(saved, progress);
  const restored = readScanProgress(saved, start + 90 * 60 * 1000);
  assert.equal(restored.nextPage, 'synthetic-page-two');
  assert.equal(restored.windowStart, 1790942400);
  assert.equal(restored.days, 14);
  assert.equal(restored.limit, 150);
  assert.equal(restored.totals.skipped, 70);
  assert.equal(restored.batches, 1);
});

test('continuing adds counts and replaces the cursor until completion', () => {
  const first = advanceScanProgress(null, 14, 150, firstBatch);
  const next = advanceScanProgress(first, 14, 150, {
    window_start: 1790942400, next_page_token: null,
    scanned: 30, skipped: 20, saved: 2, needs_review: 3, ignored_job_board: 8,
  });
  assert.equal(next.nextPage, '');
  assert.equal(next.batches, 2);
  assert.deepEqual(next.totals, { scanned: 110, skipped: 90, saved: 6, needs_review: 9, ignored_job_board: 20 });
});

test('expired and damaged saved positions cannot be resumed', () => {
  const saved = storage();
  writeScanProgress(saved, advanceScanProgress(null, 14, 150, firstBatch));
  assert.equal(readScanProgress(saved, start + 25 * 60 * 60 * 1000), null);
  const damaged = { getItem: () => '{broken', removeItem() {} };
  assert.equal(readScanProgress(damaged, start), null);
});

test('starting over removes the old position and resets totals', () => {
  const saved = storage();
  writeScanProgress(saved, advanceScanProgress(null, 14, 150, firstBatch));
  writeScanProgress(saved, null);
  assert.equal(readScanProgress(saved, start), null);
  assert.equal(advanceScanProgress(null, 14, 150, firstBatch).batches, 1);
});

test('blocked storage does not prevent scanning', () => {
  const blocked = { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); }, removeItem() { throw new Error('blocked'); } };
  assert.equal(readScanProgress(blocked, start), null);
  assert.doesNotThrow(() => writeScanProgress(blocked, advanceScanProgress(null, 14, 150, firstBatch)));
});
