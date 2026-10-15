import test from 'node:test';
import assert from 'node:assert/strict';
import { partitionActions, nextSelection } from '../src/dailyQueue.ts';
import type { NextAction } from '../src/types.ts';

const action = (id: string, date: string | null, kind: NextAction['kind'] = 'followup', state: NextAction['state'] = 'waiting'): NextAction => ({
  application_id: id, job_id: id, title: 'Analyst', company: 'Example', kind, date, state,
  label: kind, due_date: null, reason: 'Confirmed event', basis: 'Application submitted', followup_count: 0,
});

test('today uses the selected timezone, with date first, same-day priority and undated last', () => {
  const items = [action('undated', null, 'record_review'), action('today-followup', '2026-10-14'),
    action('tomorrow', '2026-10-15'), action('overdue', '2026-10-13'), action('today-interview', '2026-10-14', 'interview'),
    action('paused', '2026-10-01', 'followup', 'paused')];
  const result = partitionActions(items, 'America/Chicago', new Date('2026-10-15T02:00:00Z'));
  assert.deepEqual(result.today.map(a => a.application_id), ['overdue', 'today-interview', 'today-followup', 'undated']);
  assert.deepEqual(result.upcoming.map(a => a.application_id), ['tomorrow']);
  assert.equal(result.overdue, 1);
  assert.equal(items[0].application_id, 'undated');
});

test('saving advances to the next visible record, then wraps without inventing completion', () => {
  const items = [action('a', null), action('b', null), action('c', null)];
  assert.equal(nextSelection(items, 'a'), 'b');
  assert.equal(nextSelection(items, 'c'), 'a');
  assert.equal(nextSelection(items.slice(0, 1), 'a'), null);
  assert.equal(nextSelection([], 'a'), null);
});
