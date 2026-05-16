import { useEffect, useState } from 'react';
import type { CodeLanguage } from '../../guideTypes';

const STORAGE_KEY = 'rounds:guide:coding:language';
const DEFAULT: CodeLanguage = 'python';

function read(): CodeLanguage {
  if (typeof window === 'undefined') return DEFAULT;
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === 'python' || stored === 'javascript' || stored === 'java') return stored;
  return DEFAULT;
}

export function useCodeLanguage() {
  const [language, setLanguageState] = useState<CodeLanguage>(read);
  useEffect(() => {
    const handler = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY && event.newValue) {
        if (event.newValue === 'python' || event.newValue === 'javascript' || event.newValue === 'java') {
          setLanguageState(event.newValue);
        }
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);
  const setLanguage = (next: CodeLanguage) => {
    setLanguageState(next);
    if (typeof window !== 'undefined') window.localStorage.setItem(STORAGE_KEY, next);
  };
  return [language, setLanguage] as const;
}
