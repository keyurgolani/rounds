import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import type { Session } from '@supabase/supabase-js';
import { supabase, supabaseEnabled } from '../lib/supabase';

export type AuthProvider = 'google' | 'github' | 'email';

export type User = {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  provider: AuthProvider;
  bio?: string;
  target?: string;
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

const MOCK_STORAGE_KEY = 'rounds.auth.v1';

// ---------- Mock (local) store ----------

function loadMock(): User | null {
  try {
    const raw = localStorage.getItem(MOCK_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

function saveMock(u: User | null) {
  try {
    if (u) localStorage.setItem(MOCK_STORAGE_KEY, JSON.stringify(u));
    else localStorage.removeItem(MOCK_STORAGE_KEY);
  } catch {
    /* noop */
  }
}

function makeId() {
  return Math.random().toString(36).slice(2, 10);
}

// ---------- Mapping Supabase session → User ----------

function userFromSession(
  session: Session | null,
  profile?: { name?: string | null; bio?: string | null; target?: string | null }
): User | null {
  const u = session?.user;
  if (!u) return null;
  const meta = (u.user_metadata ?? {}) as Record<string, string | undefined>;
  const rawProvider = (u.app_metadata?.provider ?? 'email') as string;
  const provider: AuthProvider =
    rawProvider === 'google' ? 'google' : rawProvider === 'github' ? 'github' : 'email';
  return {
    id: u.id,
    email: u.email ?? '',
    name:
      profile?.name ??
      meta.name ??
      meta.full_name ??
      (u.email ? u.email.split('@')[0] : 'User'),
    avatar: meta.avatar_url,
    provider,
    bio: profile?.bio ?? '',
    target: profile?.target ?? '',
    createdAt: u.created_at ?? new Date().toISOString(),
  };
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() =>
    supabaseEnabled ? null : loadMock()
  );
  const [ready, setReady] = useState(!supabaseEnabled);
  const sessionSub = useRef<{ unsubscribe: () => void } | null>(null);

  // ---- Supabase-backed branch ------------------------------------------
  useEffect(() => {
    if (!supabase) return;

    async function hydrate(session: Session | null) {
      if (!session) {
        setUser(null);
        setReady(true);
        return;
      }
      let profile: { name?: string | null; bio?: string | null; target?: string | null } | undefined;
      try {
        const { data } = await supabase!
          .from('profiles')
          .select('name, bio, target')
          .eq('id', session.user.id)
          .maybeSingle();
        profile = data ?? undefined;
      } catch {
        /* trigger may not have fired yet on a fresh signup; ignore */
      }
      setUser(userFromSession(session, profile));
      setReady(true);
    }

    supabase.auth.getSession().then(({ data }) => hydrate(data.session));
    const { data: listener } = supabase.auth.onAuthStateChange((_event, s) => {
      hydrate(s);
    });
    sessionSub.current = listener.subscription;
    return () => sessionSub.current?.unsubscribe();
  }, []);

  // ---- Mock branch ------------------------------------------------------
  useEffect(() => {
    if (supabaseEnabled) return;
    saveMock(user);
  }, [user]);

  // ---- Public API ------------------------------------------------------

  async function login(email: string, password: string) {
    if (!email.trim() || !password) throw new Error('Email and password required');
    if (supabase) {
      const { error } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password,
      });
      if (error) throw new Error(error.message);
      return;
    }
    const existing = loadMock();
    if (existing && existing.email === email.trim()) {
      setUser(existing);
      return;
    }
    const name = email
      .split('@')[0]
      .replace(/[._-]+/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
    setUser({
      id: makeId(),
      name,
      email: email.trim(),
      provider: 'email',
      createdAt: new Date().toISOString(),
    });
  }

  async function signup(name: string, email: string, password: string) {
    if (!name.trim() || !email.trim() || !password) throw new Error('All fields required');
    if (supabase) {
      const { error } = await supabase.auth.signUp({
        email: email.trim(),
        password,
        options: { data: { name: name.trim() } },
      });
      if (error) throw new Error(error.message);
      return;
    }
    setUser({
      id: makeId(),
      name: name.trim(),
      email: email.trim(),
      provider: 'email',
      createdAt: new Date().toISOString(),
    });
  }

  async function oauthSignIn(provider: 'google' | 'github') {
    if (supabase) {
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo:
            typeof window !== 'undefined' ? `${window.location.origin}/dashboard` : undefined,
        },
      });
      if (error) throw new Error(error.message);
      return;
    }
    const suffix = provider === 'google' ? 'gmail.com' : 'users.noreply.github.com';
    const demoName = provider === 'google' ? 'Anika Shah' : 'octo-cat';
    setUser({
      id: makeId(),
      name: demoName,
      email: `${demoName.toLowerCase().replace(/\s+/g, '.')}@${suffix}`,
      provider,
      createdAt: new Date().toISOString(),
    });
  }

  async function logout() {
    if (supabase) {
      await supabase.auth.signOut();
      return;
    }
    setUser(null);
  }

  async function updateProfile(patch: Partial<User>) {
    if (supabase && user) {
      const { error } = await supabase
        .from('profiles')
        .upsert({
          id: user.id,
          name: patch.name ?? user.name,
          bio: patch.bio ?? user.bio ?? '',
          target: patch.target ?? user.target ?? '',
        });
      if (error) throw new Error(error.message);
      setUser({ ...user, ...patch });
      return;
    }
    setUser((u) => (u ? { ...u, ...patch } : u));
  }

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
