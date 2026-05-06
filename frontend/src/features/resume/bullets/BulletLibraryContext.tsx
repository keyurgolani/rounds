// Lightweight context that bridges editor rows to the central
// BulletLibraryDrawer. Editors call `pickBullet()` and await a single
// selection; the provider opens the drawer in picker mode and resolves
// the promise when the user clicks Insert (or closes empty-handed).
//
// Putting this in a context (instead of prop-drilling a callback
// through Studio → Editor → StringList) keeps the editors decoupled
// from where the drawer lives, and makes it easy to surface the
// library elsewhere (e.g. from an Anecdote page) without rewiring.

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import type { Bullet } from '../types';

type Resolver = (bullet: Bullet | null) => void;

type Mode = 'closed' | 'manage' | 'picker';

type ContextValue = {
  mode: Mode;
  // Returns the picked bullet, or null if the user dismissed the drawer.
  pickBullet: () => Promise<Bullet | null>;
  // Open in browse/edit mode (no resolver).
  openManager: () => void;
  // Internal: drawer calls these to settle outstanding pick promises.
  resolve: (bullet: Bullet | null) => void;
  close: () => void;
};

const Ctx = createContext<ContextValue | null>(null);

export function BulletLibraryProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>('closed');
  const resolverRef = useRef<Resolver | null>(null);

  const pickBullet = useCallback((): Promise<Bullet | null> => {
    return new Promise((resolve) => {
      // Cancel any in-flight pick; only one drawer at a time.
      const previous = resolverRef.current;
      if (previous) previous(null);
      resolverRef.current = resolve;
      setMode('picker');
    });
  }, []);

  const openManager = useCallback(() => {
    const previous = resolverRef.current;
    if (previous) {
      previous(null);
      resolverRef.current = null;
    }
    setMode('manage');
  }, []);

  const resolve = useCallback((bullet: Bullet | null) => {
    const r = resolverRef.current;
    resolverRef.current = null;
    if (r) r(bullet);
    setMode('closed');
  }, []);

  const close = useCallback(() => {
    resolve(null);
  }, [resolve]);

  const value = useMemo(
    () => ({ mode, pickBullet, openManager, resolve, close }),
    [mode, pickBullet, openManager, resolve, close],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useBulletLibrary(): ContextValue {
  const ctx = useContext(Ctx);
  if (!ctx) {
    throw new Error('useBulletLibrary must be used inside <BulletLibraryProvider>');
  }
  return ctx;
}

// Optional variant for editors that may render outside a Studio (which
// hosts the provider). Returns no-op callbacks instead of throwing.
export function useOptionalBulletLibrary(): ContextValue | null {
  return useContext(Ctx);
}
