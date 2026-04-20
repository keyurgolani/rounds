import { useCallback, useEffect, useState } from 'react';
import type { PracticeStatus } from '../components/shell/StatusDot';

const STATUS_KEY = 'rounds.practiceStatus.v1';

type Track = 'system' | 'coding' | 'behavioral';

function loadStatusMap(): Record<string, PracticeStatus> {
  try {
    return JSON.parse(localStorage.getItem(STATUS_KEY) ?? '{}');
  } catch {
    return {};
  }
}

function saveStatusMap(m: Record<string, PracticeStatus>) {
  try {
    localStorage.setItem(STATUS_KEY, JSON.stringify(m));
  } catch {
    /* noop */
  }
}

export function usePracticeStatus(
  track: Track,
  id: number | string,
  fallback: PracticeStatus = 'todo'
): [PracticeStatus, (s: PracticeStatus) => void] {
  const key = `${track}:${id}`;
  const [status, setStatus] = useState<PracticeStatus>(() => {
    return loadStatusMap()[key] ?? fallback;
  });

  useEffect(() => {
    const on = (e: Event) => {
      const detail = (e as CustomEvent<{ key: string; status: PracticeStatus }>).detail;
      if (detail?.key === key) {
        setStatus(loadStatusMap()[key] ?? fallback);
      }
    };
    window.addEventListener('rounds:status', on);
    return () => window.removeEventListener('rounds:status', on);
  }, [key, fallback]);

  const set = useCallback(
    (s: PracticeStatus) => {
      const m = loadStatusMap();
      m[key] = s;
      saveStatusMap(m);
      setStatus(s);
      window.dispatchEvent(new CustomEvent('rounds:status', { detail: { key, status: s } }));
    },
    [key]
  );

  return [status, set];
}

export function useStatusMapVersion() {
  const [v, setV] = useState(0);
  useEffect(() => {
    const on = () => setV((x) => x + 1);
    window.addEventListener('rounds:status', on);
    return () => window.removeEventListener('rounds:status', on);
  }, []);
  return v;
}

export function effectiveStatus(
  track: Track,
  id: number | string,
  fallback: PracticeStatus = 'todo'
) {
  return loadStatusMap()[`${track}:${id}`] ?? fallback;
}
