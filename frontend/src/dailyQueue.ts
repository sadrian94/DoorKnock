import type { NextAction } from './types';
import { calendarDay } from './time.ts';

const priority: Record<NextAction['kind'], number> = {
  interview: 0, interview_review: 0, assessment: 0, thank_you: 1, record_review: 2,
  followup: 3, status_check: 4, paused: 5, closed: 6,
};

export function partitionActions(items: NextAction[], timezone: string, now = new Date()) {
  const today = calendarDay(now.toISOString(), timezone)!;
  const sorted = items.filter(item => !['paused', 'closed'].includes(item.state)).slice().sort((a, b) =>
    Number(!a.date) - Number(!b.date) || (a.date || '').localeCompare(b.date || '') ||
    priority[a.kind] - priority[b.kind] || a.company.localeCompare(b.company) || a.title.localeCompare(b.title));
  return {
    today: sorted.filter(item => !item.date || item.date <= today),
    upcoming: sorted.filter(item => item.date && item.date > today),
    overdue: sorted.filter(item => item.date && item.date < today).length,
  };
}

export function nextSelection(items: NextAction[], currentId: string): string | null {
  if (items.length < 2) return null;
  const index = items.findIndex(item => item.application_id === currentId);
  return items[(index + 1) % items.length].application_id;
}
