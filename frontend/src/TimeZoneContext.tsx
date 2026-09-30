import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { TimeSettingsContext } from './timeSettings';
import type { TimeSettings } from './timeSettings';

export function TimeZoneProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<TimeSettings | null>(null);
  const [error, setError] = useState('');
  const load = () => {
    return fetch('/api/settings/time')
      .then(response => {
        if (!response.ok) throw new Error('Could not load the time zone. Check the backend connection.');
        return response.json() as Promise<TimeSettings>;
      })
      .then(setSettings)
      .catch(err => setError(err instanceof Error ? err.message : 'Could not load the time zone.'));
  };
  useEffect(() => { void load(); }, []);
  if (!settings) return <div className="p-8 text-slate-300" role="status">
    {error || 'Loading time settings…'}
    {error && <button className="ml-4 underline" onClick={() => void load()}>Retry</button>}
  </div>;
  return <TimeSettingsContext.Provider value={{ settings, setTimezone: timezone => setSettings(current => current ? { ...current, timezone } : current) }}>
    {children}
  </TimeSettingsContext.Provider>;
}
