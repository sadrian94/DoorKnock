import { createContext, useContext } from 'react';

export type TimeSettings = { timezone: string; available_timezones: string[]; current_time: string };
export type TimeContext = { settings: TimeSettings; setTimezone: (timezone: string) => void };
export const TimeSettingsContext = createContext<TimeContext | null>(null);

export function useTimeSettings(): TimeContext {
  const context = useContext(TimeSettingsContext);
  if (!context) throw new Error('TimeZoneProvider is required');
  return context;
}
