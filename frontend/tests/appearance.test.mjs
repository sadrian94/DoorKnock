import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import vm from 'node:vm';

const path = new URL('../public/appearance-init.js', import.meta.url);
const source = existsSync(path) ? readFileSync(path, 'utf8') : '';
const key = 'doorknock_appearance';

function browser(saved, { dark = false, blocked = false } = {}) {
  const storage = new Map(saved === undefined ? [] : [[key, saved]]);
  const events = new Map();
  const media = { matches: dark, addEventListener: (_, listener) => { media.listener = listener; } };
  const document = { documentElement: { dataset: {}, style: {} } };
  const window = {
    localStorage: {
      getItem(name) { if (blocked) throw new Error('Storage disabled'); return storage.get(name) ?? null; },
      setItem(name, value) { if (blocked) throw new Error('Storage disabled'); storage.set(name, value); },
    },
    matchMedia: () => media,
    addEventListener: (type, listener) => events.set(type, listener),
  };
  vm.runInNewContext(source, { window, document });
  const api = window.DoorKnockAppearance;
  assert.ok(api, 'Appearance should initialize before the React application loads');
  return { api, document, storage, media, events };
}

test('fresh and damaged preferences retain Classic regardless of system appearance', () => {
  for (const saved of [undefined, '{broken', 'null', '[]', '{"style":"unknown","mode":"light"}']) {
    const { document, storage } = browser(saved, { dark: false });
    assert.equal(document.documentElement.dataset.appearance, 'classic');
    assert.equal(document.documentElement.dataset.colorMode, 'dark');
    assert.equal(document.documentElement.style.colorScheme, 'normal');
    assert.equal(storage.get(key), saved, 'Reading preferences must not rewrite storage');
  }
});

test('Calm honors explicit modes and follows system changes only in System mode', () => {
  const { api, document, media, storage } = browser('{"style":"calm","mode":"system"}');
  assert.equal(document.documentElement.dataset.colorMode, 'light');
  media.matches = true; media.listener();
  assert.equal(document.documentElement.dataset.colorMode, 'dark');
  api.setPreference({ style: 'calm', mode: 'light' });
  media.listener();
  assert.equal(document.documentElement.dataset.colorMode, 'light');
  assert.equal(document.documentElement.style.colorScheme, 'light');
  assert.equal(JSON.parse(storage.get(key)).mode, 'light');
  api.setPreference({ style: 'classic', mode: 'system' });
  media.matches = false; media.listener();
  assert.equal(document.documentElement.dataset.colorMode, 'dark');
});

test('storage denial still allows appearance changes for the current session', () => {
  const { api, document } = browser(undefined, { blocked: true });
  assert.equal(api.setPreference({ style: 'calm', mode: 'dark' }), false);
  assert.equal(document.documentElement.dataset.appearance, 'calm');
  assert.equal(document.documentElement.dataset.colorMode, 'dark');
  assert.equal(api.getSnapshot().style, 'calm');
});

test('cross-tab changes notify subscribers and unsubscribe stops notifications', () => {
  const { api, document, events } = browser();
  let changes = 0;
  const unsubscribe = api.subscribe(() => { changes += 1; });
  events.get('storage')({ key, newValue: '{"style":"calm","mode":"dark"}' });
  assert.equal(api.getSnapshot().style, 'calm');
  assert.equal(document.documentElement.dataset.colorMode, 'dark');
  assert.equal(changes, 1);
  unsubscribe();
  events.get('storage')({ key, newValue: null });
  assert.equal(document.documentElement.dataset.appearance, 'classic');
  assert.equal(changes, 1);
});

test('preference snapshots are stable and duplicate selections do not notify', () => {
  const { api } = browser();
  assert.equal(api.getSnapshot(), api.getSnapshot());
  let changes = 0;
  api.subscribe(() => { changes += 1; });
  api.setPreference({ style: 'calm', mode: 'light' });
  api.setPreference({ style: 'calm', mode: 'light' });
  assert.equal(changes, 1);
});

test('Calm navigation counts and filled actions retain readable text contrast', () => {
  const css = readFileSync(new URL('../src/appearance.css', import.meta.url), 'utf8');
  const luminance = rgb => rgb.map(value => value / 255)
    .map(value => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4)
    .reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
  const contrast = (a, b) => (Math.max(luminance(a), luminance(b)) + 0.05)
    / (Math.min(luminance(a), luminance(b)) + 0.05);
  for (const [, mode, block] of css.matchAll(/html\[data-appearance="calm"\]\[data-color-mode="(light|dark)"\] \{([\s\S]*?)\n\}/g)) {
    const palette = Object.fromEntries([...block.matchAll(/--ui-([\w-]+): ([\d ]+);/g)]
      .map(([, name, value]) => [name, value.split(' ').map(Number)]));
    const badgeBackground = palette['fill-amber-800'].map((value, index) => value * 0.8 + palette['fill-amber-600'][index] * 0.2);
    assert.ok(contrast(palette['ink-amber-100'], badgeBackground) >= 4.5, `${mode}: selected navigation count`);
    for (const tone of ['amber', 'emerald', 'blue', 'red']) {
      for (const shade of ['500', '600']) {
        assert.ok(contrast(palette[tone === 'amber' ? 'on-action' : 'on-color'], palette[`fill-${tone}-${shade}`]) >= 4.5,
          `${mode}: ${tone} ${shade} action text`);
      }
    }
  }
});
