import { useState } from 'react';
import { useAppearance } from '../appearance';
import type { AppearancePreference } from '../appearance';

export function AppearanceSettings() {
  const { preference, setPreference } = useAppearance();
  const [notice, setNotice] = useState('');

  function change(next: AppearancePreference) {
    const saved = setPreference(next);
    setNotice(saved ? 'Appearance saved in this browser.'
      : 'Appearance changed for this session. Browser storage is unavailable.');
  }

  return (
    <section aria-labelledby="appearance-heading" className="rounded-xl border border-ui-line bg-ui-panel p-6 space-y-5">
      <div>
        <h3 id="appearance-heading" className="text-lg font-semibold text-ui-heading">Appearance</h3>
        <p className="mt-1 text-sm text-ui-muted">Choose a style. Your current page, drafts and application progress stay in place.</p>
      </div>
      <fieldset>
        <legend className="mb-3 text-sm font-medium text-ui-secondary">Interface style</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          {(['classic', 'calm'] as const).map(style => (
            <label key={style} className={`appearance-choice cursor-pointer rounded-lg border p-4 ${preference.style === style ? 'border-ui-ink-amber-500 bg-ui-fill-amber-950/20' : 'border-ui-line bg-ui-page'}`}>
              <div className={`appearance-swatch appearance-swatch-${style}`} aria-hidden="true"><span /><span /><span /></div>
              <span className="mt-3 flex items-center gap-2 text-sm font-semibold text-ui-heading">
                <input type="radio" name="appearance-style" value={style} checked={preference.style === style}
                  onChange={() => change({ ...preference, style })} className="accent-ui-ink-amber-500" />
                {style === 'classic' ? 'Classic' : 'Calm'}
              </span>
              <span className="mt-1 block text-xs text-ui-muted">{style === 'classic' ? 'Original dark style · default' : 'Softer surfaces, more space, restrained accents'}</span>
            </label>
          ))}
        </div>
      </fieldset>
      {preference.style === 'calm' && <label className="block text-sm font-medium text-ui-secondary" htmlFor="appearance-mode">
        Calm color mode
        <select id="appearance-mode" value={preference.mode}
          onChange={event => change({ ...preference, mode: event.target.value as AppearancePreference['mode'] })}
          className="mt-2 block w-full rounded-lg border border-ui-line bg-ui-page px-3 py-2 text-ui-heading">
          <option value="light">Light</option><option value="dark">Dark</option><option value="system">Follow system</option>
        </select>
      </label>}
      {notice && <p role="status" className="text-sm text-ui-body">{notice}</p>}
    </section>
  );
}
