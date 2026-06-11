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

const DEMO_COLLECTIONS_IN_DELETE_ORDER = [
  'todos',
  'code_drafts',
  'offers',
  'user_preferences',
  'user_progress',
  'interview_rounds',
  'applications',
  'campaigns',
  'experience_anecdotes',
];

async function resetDemoUser(record: AuthRecord): Promise<void> {
  if (!record?.id) return;
  const userId = record.id;

  for (const collection of DEMO_COLLECTIONS_IN_DELETE_ORDER) {
    const rows = await pb.collection(collection).getFullList<{ id: string }>({
      filter: `user = "${userId}"`,
      fields: 'id',
    });
    await Promise.all(rows.map((row) => pb.collection(collection).delete(row.id)));
  }

  const updated = await pb.collection('users').update(userId, {
    name: 'Rounds Demo',
    bio: 'Disposable hosted demo account. Changes reset on logout.',
    target: 'Explore Rounds',
    demo_run_used: false,
    demo_evaluate_used: false,
  });
  pb.authStore.save(pb.authStore.token, updated);

  clearDemoStorage(userId);
}

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
  } catch {
    /* storage may be unavailable */
  }
}

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

  const logout = useCallback(async () => {
    const record = pb.authStore.record;
    if (record && (record as unknown as { is_demo?: boolean }).is_demo === true) {
      await resetDemoUser(record);
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

export function initials(name: string) {
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();
}
