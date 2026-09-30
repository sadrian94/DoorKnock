// Explicit event instants use the selected zone. Calendar dates never shift.
const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;
const SQLITE_UTC = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?$/;
const NAIVE_ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/;

const instantDate = (value: string): Date =>
  new Date(SQLITE_UTC.test(value) ? `${value.replace(' ', 'T')}Z` : value);

export function timestampForSort(value: string | null | undefined): number {
  // An unknown legacy zone cannot be compared reliably with an event instant.
  // Keep these with missing timestamps rather than guessing the browser zone.
  if (!value || NAIVE_ISO.test(value)) return NaN;
  return instantDate(value).getTime();
}

export function calendarDay(value: string, timeZone: string): string | null {
  if (DATE_ONLY.test(value) || NAIVE_ISO.test(value)) {
    const day = value.slice(0, 10);
    const date = new Date(`${day}T00:00:00Z`);
    return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === day ? day : null;
  }
  const date = instantDate(value);
  if (Number.isNaN(date.getTime())) return null;
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone, year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(date);
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find(p => p.type === type)?.value;
  return `${part('year')}-${part('month')}-${part('day')}`;
}

export function formatDate(value: string, timeZone: string, options: Intl.DateTimeFormatOptions = {}): string {
  const day = calendarDay(value, timeZone);
  if (!day) return value;
  // Format the calendar day in UTC, rather than parsing it as browser midnight.
  return new Intl.DateTimeFormat('en-US', { ...options, timeZone: 'UTC' })
    .format(new Date(`${day}T12:00:00Z`));
}

export function formatDateTime(value: string, timeZone: string): string {
  if (NAIVE_ISO.test(value)) return `${value.replace('T', ' ')} (time zone not recorded)`;
  if (DATE_ONLY.test(value)) return formatDate(value, timeZone);
  const date = instantDate(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', {
    timeZone, year: 'numeric', month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit', second: '2-digit', timeZoneName: 'short',
  }).format(date);
}

export function daysAgo(value: string | undefined, timeZone: string, now = new Date()): string | null {
  if (!value) return null;
  const day = calendarDay(value, timeZone);
  const today = calendarDay(now.toISOString(), timeZone);
  if (!day || !today) return null;
  const diff = Math.round((Date.parse(today) - Date.parse(day)) / 86400000);
  return diff <= 0 ? 'Today' : `${diff}d ago`;
}

export const hasUnknownTimeZone = (value: string): boolean => NAIVE_ISO.test(value);
