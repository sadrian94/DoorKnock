// Loaded synchronously before React so loading and error screens use the saved appearance.
(() => {
  const key = 'doorknock_appearance';
  const defaults = { style: 'classic', mode: 'system' };
  const listeners = new Set();
  const media = window.matchMedia?.('(prefers-color-scheme: dark)');

  function normalize(value) {
    return {
      style: value?.style === 'calm' ? 'calm' : 'classic',
      mode: ['light', 'dark', 'system'].includes(value?.mode) ? value.mode : 'system',
    };
  }

  function parse(value) {
    try { return normalize(JSON.parse(value)); }
    catch { return { ...defaults }; }
  }

  let preference;
  try { preference = parse(window.localStorage.getItem(key)); }
  catch { preference = { ...defaults }; }

  function apply() {
    const mode = preference.style === 'classic' ? 'dark'
      : preference.mode === 'system' ? (media?.matches ? 'dark' : 'light') : preference.mode;
    const root = document.documentElement;
    root.dataset.appearance = preference.style;
    root.dataset.colorMode = mode;
    // Classic retains the original native-control behavior as well as its colors.
    root.style.colorScheme = preference.style === 'classic' ? 'normal' : mode;
  }

  function update(next) {
    const changed = next.style !== preference.style || next.mode !== preference.mode;
    if (changed) preference = Object.freeze(next);
    apply();
    if (changed) listeners.forEach(listener => listener());
  }

  preference = Object.freeze(preference);
  window.DoorKnockAppearance = {
    getSnapshot: () => preference,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    setPreference(value) {
      update(normalize(value));
      try { window.localStorage.setItem(key, JSON.stringify(preference)); return true; }
      catch { return false; }
    },
  };

  media?.addEventListener('change', () => {
    if (preference.style === 'calm' && preference.mode === 'system') apply();
  });
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) update(parse(event.newValue));
  });
  apply();
})();
