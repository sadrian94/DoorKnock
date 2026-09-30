import { test } from 'node:test';
import assert from 'node:assert/strict';
import { calendarDay, daysAgo, formatDate, formatDateTime } from '../src/time.ts';

test('timestamps use the selected timezone while calendar dates retain their day', () => {
  assert.equal(calendarDay('2026-09-30T02:00:00Z', 'America/Chicago'), '2026-09-29');
  assert.equal(calendarDay('2026-09-30T02:00:00Z', 'Asia/Hong_Kong'), '2026-09-30');
  assert.equal(calendarDay('2026-09-30', 'America/Chicago'), '2026-09-30');
  assert.equal(formatDate('2026-09-30', 'America/Chicago', { month: 'short', day: 'numeric' }), 'Sep 30');
});

test('SQLite legacy timestamps are UTC, but legacy naive ISO values stay unconverted', () => {
  assert.equal(calendarDay('2026-09-30 02:00:00', 'America/Chicago'), '2026-09-29');
  assert.equal(calendarDay('2026-09-30T02:00:00', 'America/Chicago'), '2026-09-30');
  assert.match(formatDateTime('2026-09-30T02:00:00', 'Asia/Hong_Kong'), /time zone not recorded/);
});

test('elapsed days follow calendar boundaries across DST and midnight', () => {
  assert.equal(daysAgo('2026-03-07', 'America/Chicago', new Date('2026-03-09T05:30:00Z')), '2d ago');
  assert.equal(daysAgo('2026-09-29', 'America/Chicago', new Date('2026-09-30T02:00:00Z')), 'Today');
  assert.equal(daysAgo('invalid', 'America/Chicago'), null);
  assert.equal(formatDate('invalid', 'America/Chicago'), 'invalid');
  assert.equal(calendarDay('2026-99-99', 'America/Chicago'), null);
  assert.equal(formatDate('2026-99-99', 'America/Chicago'), '2026-99-99');
});
