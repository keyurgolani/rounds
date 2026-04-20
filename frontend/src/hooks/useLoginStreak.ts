import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthProvider';

// Login-based streak ledger.
//
// Every time the app loads while the user is signed in, today's date is
// appended to the ledger for that user. Consecutive ledger days ending
// today form the current streak; the longest observed run is preserved.
//
// Per-user storage key so switching accounts doesn't blend runs.

const BASE_KEY = 'rounds.loginStreak.v1';

type Ledger = {
  dates: string[];   // ISO YYYY-MM-DD, sorted ascending, unique
  longest: number;
};

function keyFor(userId: string | null): string {
  return userId ? `${BASE_KEY}:${userId}` : BASE_KEY;
}

function load(userId: string | null): Ledger {
  try {
    const raw = localStorage.getItem(keyFor(userId));
    if (!raw) return { dates: [], longest: 0 };
    const parsed = JSON.parse(raw) as Ledger;
    return {
      dates: Array.isArray(parsed.dates) ? parsed.dates : [],
      longest: typeof parsed.longest === 'number' ? parsed.longest : 0,
    };
  } catch {
    return { dates: [], longest: 0 };
  }
}

function save(userId: string | null, l: Ledger) {
  try {
    localStorage.setItem(keyFor(userId), JSON.stringify(l));
  } catch {
    /* noop */
  }
}

function today(): string {
  const d = new Date();
  return fmt(d);
}

function fmt(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function runEndingAt(dates: string[], end: string): number {
  const set = new Set(dates);
  if (!set.has(end)) return 0;
  let run = 0;
  let cur = end;
  while (set.has(cur)) {
    run += 1;
    const d = new Date(`${cur}T00:00:00`);
    d.setDate(d.getDate() - 1);
    cur = fmt(d);
  }
  return run;
}

function recordLogin(userId: string | null): Ledger {
  const now = load(userId);
  const t = today();
  if (now.dates.includes(t)) return now;
  const merged = [...now.dates, t].sort();
  const run = runEndingAt(merged, t);
  const longest = Math.max(now.longest, run);
  const next: Ledger = { dates: merged.slice(-365), longest };
  save(userId, next);
  return next;
}

export type LoginStreakInfo = {
  current: number;
  longest: number;
  activeToday: boolean;
  last7: boolean[];         // 7 entries, oldest first, today last
  last30: { date: string; active: boolean }[];
  totalDays: number;
  firstLogin: string | null;
  recent: string[];         // ISO dates, most recent first, up to 15
};

function compute(userId: string | null): LoginStreakInfo {
  const { dates, longest } = load(userId);
  const set = new Set(dates);
  const t = today();
  const current = runEndingAt(dates, t);
  const activeToday = set.has(t);

  const last7: boolean[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(`${t}T00:00:00`);
    d.setDate(d.getDate() - i);
    last7.push(set.has(fmt(d)));
  }
  const last30: { date: string; active: boolean }[] = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date(`${t}T00:00:00`);
    d.setDate(d.getDate() - i);
    const k = fmt(d);
    last30.push({ date: k, active: set.has(k) });
  }
  const bumpedLongest = Math.max(longest, current);
  if (bumpedLongest !== longest) {
    save(userId, { dates, longest: bumpedLongest });
  }
  const recent = [...dates].reverse().slice(0, 15);
  return {
    current,
    longest: bumpedLongest,
    activeToday,
    last7,
    last30,
    totalDays: dates.length,
    firstLogin: dates[0] ?? null,
    recent,
  };
}

export function useLoginStreak(): LoginStreakInfo {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const [info, setInfo] = useState<LoginStreakInfo>(() => {
    if (userId) recordLogin(userId);
    return compute(userId);
  });

  // Record + recompute whenever the active user changes (login, logout,
  // switching accounts). Skip recording when logged-out.
  useEffect(() => {
    if (userId) recordLogin(userId);
    setInfo(compute(userId));
  }, [userId]);

  // Recompute when focus returns (crossed midnight while idle).
  useEffect(() => {
    const onFocus = () => {
      if (userId) recordLogin(userId);
      setInfo(compute(userId));
    };
    window.addEventListener('focus', onFocus);
    const id = window.setInterval(onFocus, 10 * 60 * 1000);
    return () => {
      window.removeEventListener('focus', onFocus);
      window.clearInterval(id);
    };
  }, [userId]);

  return info;
}
