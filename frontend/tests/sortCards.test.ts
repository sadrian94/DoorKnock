import { test } from 'node:test';
import assert from 'node:assert/strict';
import { sortCards } from '../src/sortCards.ts';

const cards = [
  { id: 'b', company: 'Beta', suitability_score: null, created_at: '2026-01-03', updated_at: '2026-01-01' },
  { id: 'a', company: 'Alpha', suitability_score: 80, created_at: '2026-01-01', updated_at: '2026-01-03' },
  { id: 'c', company: 'Charlie', suitability_score: 90, created_at: '2026-01-02', updated_at: '2026-01-02' },
];

test('sorts by the date field of the current view without changing the input', () => {
  assert.deepEqual(sortCards(cards, 'newest', 'created_at').map((card) => card.id), ['b', 'c', 'a']);
  assert.deepEqual(sortCards(cards, 'oldest', 'updated_at').map((card) => card.id), ['b', 'c', 'a']);
  assert.deepEqual(cards.map((card) => card.id), ['b', 'a', 'c']);
});

test('sorts company names in both directions', () => {
  assert.deepEqual(sortCards(cards, 'company-asc', 'created_at').map((card) => card.id), ['a', 'b', 'c']);
  assert.deepEqual(sortCards(cards, 'company-desc', 'created_at').map((card) => card.id), ['c', 'b', 'a']);
});

test('places missing scores and dates last in either direction', () => {
  assert.deepEqual(sortCards(cards, 'score-desc', 'created_at').map((card) => card.id), ['c', 'a', 'b']);
  assert.deepEqual(sortCards(cards, 'score-asc', 'created_at').map((card) => card.id), ['a', 'c', 'b']);
  const withoutDate = [{ id: 'missing', company: 'Delta', created_at: '' }, ...cards];
  assert.equal(sortCards(withoutDate, 'oldest', 'created_at').at(-1)?.id, 'missing');
});
