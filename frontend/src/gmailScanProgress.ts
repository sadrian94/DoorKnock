export type ScanCounts = {
  scanned: number; skipped: number; saved: number; needs_review: number; ignored_job_board: number;
};
export type ScanBatch = ScanCounts & { window_start: number; next_page_token?: string | null };
export type ScanProgress = {
  days: number; limit: number; windowStart: number; nextPage: string; batches: number; totals: ScanCounts;
};

const STORAGE_KEY = 'doorknock_gmail_scan';
const countKeys = ['scanned', 'skipped', 'saved', 'needs_review', 'ignored_job_board'] as const;

export function scanProgressFresh(progress: ScanProgress, now = Date.now()): boolean {
  const started = (progress.windowStart + progress.days * 86400) * 1000;
  return started <= now + 1000 && now - started < 86400000;
}

export function advanceScanProgress(previous: ScanProgress | null, days: number, limit: number, batch: ScanBatch): ScanProgress {
  const totals = Object.fromEntries(countKeys.map(key => [key, (previous?.totals[key] || 0) + (batch[key] || 0)])) as ScanCounts;
  return { days, limit, windowStart: batch.window_start, nextPage: batch.next_page_token || '', batches: (previous?.batches || 0) + 1, totals };
}

export function readScanProgress(storage: Pick<Storage, 'getItem' | 'removeItem'>, now = Date.now()): ScanProgress | null {
  try {
    const saved = JSON.parse(storage.getItem(STORAGE_KEY) || 'null');
    if (!saved) return null;
    if (Number.isInteger(saved.days) && saved.days >= 1 && saved.days <= 30
      && Number.isInteger(saved.limit) && saved.limit >= 100 && saved.limit <= 200
      && Number.isInteger(saved.windowStart) && saved.windowStart > 0
      && typeof saved.nextPage === 'string' && Number.isInteger(saved.batches) && saved.batches > 0
      && saved.totals && countKeys.every(key => Number.isInteger(saved.totals[key]) && saved.totals[key] >= 0)
      && scanProgressFresh(saved, now)) return saved;
    storage.removeItem(STORAGE_KEY);
  } catch { /* A damaged or unavailable cache must not block scanning. */ }
  return null;
}

export function writeScanProgress(storage: Pick<Storage, 'setItem' | 'removeItem'>, progress: ScanProgress | null): void {
  try {
    if (progress) storage.setItem(STORAGE_KEY, JSON.stringify(progress));
    else storage.removeItem(STORAGE_KEY);
  } catch { /* Scanning still works when browser storage is unavailable. */ }
}
