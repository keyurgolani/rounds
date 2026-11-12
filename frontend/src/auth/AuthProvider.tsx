import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import type { AuthRecord } from 'pocketbase';
import { pb } from '../lib/pocketbase';
import { clearDemoKeys } from '../lib/demoKeys';
import { signupConfig } from './signupConfig';

// Idle timeout: log the user out if they don't interact with the app
// for this long. Activity in any open tab counts (shared via
// localStorage) so a long-running coding session in one tab doesn't
// expire the dashboard tab next to it.
const IDLE_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const IDLE_CHECK_INTERVAL_MS = 30 * 1000;
const IDLE_STORAGE_KEY = 'rounds:last-activity-at';

export type AuthProvider = 'google' | 'github' | 'email';

export type User = {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  provider: AuthProvider;
  bio?: string;
  target?: string;
  isDemo?: boolean;
  createdAt: string;
};

type AuthContextValue = {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  oauthSignIn: (provider: 'google' | 'github') => Promise<void>;
  logout: () => Promise<void>;
  updateProfile: (patch: Partial<User>) => Promise<void>;
};

function recordToUser(record: AuthRecord | null): User | null {
  if (!record) return null;
  const r = record as unknown as Record<string, unknown> & { id: string; email?: string; created?: string };
  const provider = ((r.provider as string) ?? 'email') as AuthProvider;
  const mappedProvider: AuthProvider =
    provider === 'google' || provider === 'github' ? provider : 'email';
  const avatarField = typeof r.avatar === 'string' && r.avatar ? String(r.avatar) : undefined;
  const avatarUrl = avatarField
    ? pb.files.getURL(record as unknown as { collectionId: string; collectionName: string; id: string; [key: string]: unknown }, avatarField)
    : undefined;
  const email = (r.email as string | undefined) ?? '';
  const name =
    (typeof r.name === 'string' && r.name.trim()) ||
    (email ? email.split('@')[0] : 'User');
  return {
    id: r.id,
    email,
    name,
    avatar: avatarUrl,
    provider: mappedProvider,
    bio: typeof r.bio === 'string' ? r.bio : '',
    target: typeof r.target === 'string' ? r.target : '',
    isDemo: r.is_demo === true,
    createdAt: (r.created as string) ?? new Date().toISOString(),
  };
}

// The demo's sign-out on the server (ROUNDS-00B-L07): PocketBase clears
// what the demo account holds and puts its seeded profile back. The SPA
// waits for it at most DEMO_END_WAIT_MS and signs out either way; a sweep
// clears the account when nobody signs out.
const DEMO_END_PATH = '/api/rounds/demo/sessions/end';
const DEMO_END_WAIT_MS = 5000;

function isDemoRecord(record: AuthRecord | null): boolean {
  return Boolean(record) && (record as unknown as { is_demo?: boolean }).is_demo === true;
}

// The request starts before this returns its promise, with the token it
// was given, so a caller may clear the auth store right after.
// `keepalive` lets it finish when the page is going away.
async function endDemoSession(token: string, keepalive = false): Promise<void> {
  const controller = typeof AbortController === 'undefined' ? null : new AbortController();
  const timer = controller ? window.setTimeout(() => controller.abort(), DEMO_END_WAIT_MS) : 0;
  try {
    await fetch(pb.buildURL(DEMO_END_PATH), {
      method: 'POST',
      headers: { Authorization: token },
      keepalive,
      signal: controller?.signal,
    });
  } catch {
    /* the sweep clears the account later */
  } finally {
    if (timer) window.clearTimeout(timer);
  }
}

// What a demo session left in this browser: its code drafts and login
// streak, the current campaign, practice status, theme tweaks, and the
// activity clock, its code-run keys in session storage, and every key
// under the demo-only prefix (lib/demoKeys).
function clearDemoStorage(userId: string): void {
  try {
    const prefixes = [
      `rounds.codeDraft.v1:${userId}:`,
      `rounds.loginStreak.v1:${userId}`,
    ];
    const exact = new Set([
      'rounds.currentCampaign.v1',
      'rounds.practiceStatus.v1',
      'rounds.tweaks.v1',
      'rounds:last-activity-at',
    ]);
    const keys: string[] = [];
    for (let i = 0; i < window.localStorage.length; i += 1) {
      const key = window.localStorage.key(i);
      if (!key) continue;
      if (exact.has(key) || prefixes.some((prefix) => key.startsWith(prefix))) keys.push(key);
    }
    for (const key of keys) window.localStorage.removeItem(key);
    const jobs: string[] = [];
    for (let i = 0; i < window.sessionStorage.length; i += 1) {
      const key = window.sessionStorage.key(i);
      if (key && key.startsWith('rounds:job:')) jobs.push(key);
    }
    for (const key of jobs) window.sessionStorage.removeItem(key);
  } catch {
    /* storage may be unavailable */
  }
  clearDemoKeys();
}

// A start with no demo session clears the demo-only keys a demo session
// that ended elsewhere (a closed tab, an expired token) left behind. It
// runs once, when the app loads.
export function clearDemoKeysWithoutADemoSession(): void {
  if (!(pb.authStore.isValid && isDemoRecord(pb.authStore.record))) clearDemoKeys();
}
clearDemoKeysWithoutADemoSession();

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // The PocketBase SDK loads its token from localStorage synchronously
  // in its constructor, so authStore.isValid is already accurate by
  // the time this component mounts. Treat that as the source of truth
  // for the initial render — start `ready` at true when we already
  // know the answer, so RequireAuth never flashes to /login on a hard
  // navigation to a protected route.
  const [user, setUser] = useState<User | null>(() =>
    pb.authStore.isValid ? recordToUser(pb.authStore.record) : null,
  );
  const [ready, setReady] = useState<boolean>(() => pb.authStore.isValid === false);

  useEffect(() => {
    let cancelled = false;

    const refresh = async () => {
      if (!pb.authStore.isValid) {
        if (!cancelled) {
          setUser(null);
          setReady(true);
        }
        return;
      }
      try {
        // Background refresh to pick up edits from other tabs / devices.
        const fresh = await pb.collection('users').authRefresh();
        if (!cancelled) setUser(recordToUser(fresh.record));
      } catch (err) {
        // Distinguish auth-invalid from a transient network blip. A
        // 401/403/404 means the server rejected the token (key rotation,
        // user deleted, account disabled) — clear the stale store so
        // the UI drops back to /login. Anything else (status 0, network
        // failure) keeps the user signed in and retries next mount.
        const status = (err as { status?: number } | null)?.status ?? 0;
        if (status === 401 || status === 403 || status === 404) {
          // A rejected demo session can't reach the server's sign-out,
          // so the sweep clears the account; the browser's keys go now.
          const record = pb.authStore.record;
          if (record && isDemoRecord(record)) clearDemoStorage(record.id);
          pb.authStore.clear();
          if (!cancelled) setUser(null);
        }
      } finally {
        if (!cancelled) setReady(true);
      }
    };
    void refresh();

    const unsubscribe = pb.authStore.onChange(() => {
      if (!cancelled) setUser(recordToUser(pb.authStore.record));
    });
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, []);

  // Idle-timeout watcher. Runs only while a user is signed in. Tracks
  // the last interaction in localStorage so multiple tabs share one
  // clock — typing in tab A keeps tab B alive.
  const lastActivityRef = useRef<number>(Date.now());
  useEffect(() => {
    if (!user) return;

    const now = Date.now();
    lastActivityRef.current = now;
    try {
      window.localStorage.setItem(IDLE_STORAGE_KEY, String(now));
    } catch {
      /* storage may be unavailable in private mode — fall back to in-memory */
    }

    let lastWrite = 0;
    function markActive() {
      const t = Date.now();
      lastActivityRef.current = t;
      // Throttle the cross-tab write so mousemove doesn't hammer storage.
      if (t - lastWrite < 1000) return;
      lastWrite = t;
      try {
        window.localStorage.setItem(IDLE_STORAGE_KEY, String(t));
      } catch {
        /* ignore */
      }
    }

    function onStorage(e: StorageEvent) {
      if (e.key !== IDLE_STORAGE_KEY || !e.newValue) return;
      const t = Number(e.newValue);
      if (Number.isFinite(t)) lastActivityRef.current = t;
    }

    function onVisibility() {
      if (document.visibilityState === 'visible') markActive();
    }

    const events: (keyof WindowEventMap)[] = [
      'mousemove',
      'mousedown',
      'keydown',
      'touchstart',
      'wheel',
      'scroll',
    ];
    for (const ev of events) {
      window.addEventListener(ev, markActive, { passive: true });
    }
    window.addEventListener('storage', onStorage);
    document.addEventListener('visibilitychange', onVisibility);

    const interval = window.setInterval(() => {
      // Trust the local ref; cross-tab writes already update it via the
      // storage event. Reading localStorage on every tick would also
      // work but isn't necessary.
      if (Date.now() - lastActivityRef.current >= IDLE_TIMEOUT_MS) {
        // An idle demo session ends on the server too; keepalive lets the
        // request finish if the tab is closing.
        const record = pb.authStore.record;
        if (record && isDemoRecord(record)) {
          void endDemoSession(pb.authStore.token, true);
          clearDemoStorage(record.id);
        }
        pb.authStore.clear();
      }
    }, IDLE_CHECK_INTERVAL_MS);

    return () => {
      for (const ev of events) window.removeEventListener(ev, markActive);
      window.removeEventListener('storage', onStorage);
      document.removeEventListener('visibilitychange', onVisibility);
      window.clearInterval(interval);
    };
  }, [user]);

  const login = useCallback(async (email: string, password: string) => {
    if (!email.trim() || !password) throw new Error('Email and password required');
    await pb.collection('users').authWithPassword(email.trim(), password);
  }, []);

  const signup = useCallback(
    async (name: string, email: string, password: string) => {
      if (signupConfig.disabled) {
        throw new Error('Signups are disabled on this instance.');
      }
      if (!name.trim() || !email.trim() || !password) {
        throw new Error('All fields required');
      }
      await pb.collection('users').create({
        email: email.trim(),
        password,
        passwordConfirm: password,
        name: name.trim(),
      });
      await pb.collection('users').authWithPassword(email.trim(), password);
    },
    [],
  );

  const oauthSignIn = useCallback(async (provider: 'google' | 'github') => {
    await pb.collection('users').authWithOAuth2({ provider });
  }, []);

  // A demo sign-out clears what the demo account holds on the server and
  // what the session left in this browser, then signs out even if the
  // server didn't answer.
  const logout = useCallback(async () => {
    const record = pb.authStore.record;
    if (record && isDemoRecord(record)) {
      await endDemoSession(pb.authStore.token);
      clearDemoStorage(record.id);
    }
    pb.authStore.clear();
  }, []);

  const updateProfile = useCallback(
    async (patch: Partial<User>) => {
      if (!pb.authStore.record) return;
      const updated = await pb.collection('users').update(pb.authStore.record.id, {
        name: patch.name ?? pb.authStore.record.name,
        bio: patch.bio ?? pb.authStore.record.bio ?? '',
        target: patch.target ?? pb.authStore.record.target ?? '',
      });
      // Manually sync the authStore so onChange subscribers re-render
      // with the new name/bio/target immediately.
      pb.authStore.save(pb.authStore.token, updated);
    },
    [],
  );

  const value: AuthContextValue = {
    user,
    ready,
    login,
    signup,
    oauthSignIn,
    logout,
    updateProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

/** Whether the demo account is signed in; false outside AuthProvider. */
export function useIsDemo(): boolean {
  return useContext(AuthContext)?.user?.isDemo === true;
}

export function initials(name: string) {
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();
}
