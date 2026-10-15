import { useSyncExternalStore } from 'react';

export type AppearancePreference = {
  style: 'classic' | 'calm';
  mode: 'light' | 'dark' | 'system';
};

declare global {
  interface Window {
    DoorKnockAppearance: {
      getSnapshot: () => AppearancePreference;
      subscribe: (listener: () => void) => () => void;
      setPreference: (preference: AppearancePreference) => boolean;
    };
  }
}

export function useAppearance() {
  const store = window.DoorKnockAppearance;
  const preference = useSyncExternalStore(store.subscribe, store.getSnapshot);
  return { preference, setPreference: store.setPreference };
}
