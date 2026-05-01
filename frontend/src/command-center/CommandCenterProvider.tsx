import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useLocation } from 'react-router-dom';

type CommandCenterState = {
  isOpen: boolean;
  viewId: string | null;
};

type CommandCenterApi = CommandCenterState & {
  open: () => void;
  openView: (id: string) => void;
  back: () => void;
  close: () => void;
};

const Ctx = createContext<CommandCenterApi | null>(null);

export function useCommandCenter(): CommandCenterApi {
  const v = useContext(Ctx);
  if (!v) throw new Error('useCommandCenter must be used inside CommandCenterProvider');
  return v;
}

export function CommandCenterProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<CommandCenterState>({ isOpen: false, viewId: null });
  const location = useLocation();

  // Captured at the moment the modal opens (before any autoFocus inside the
  // modal moves activeElement away). Restored on close so keyboard users
  // land back at the trigger.
  const triggerRef = useRef<HTMLElement | null>(null);
  const wasOpenRef = useRef(false);

  const captureTrigger = () => {
    triggerRef.current = (document.activeElement as HTMLElement | null) ?? null;
  };

  const open = useCallback(() => {
    captureTrigger();
    setState({ isOpen: true, viewId: null });
  }, []);
  const openView = useCallback((id: string) => {
    captureTrigger();
    setState({ isOpen: true, viewId: id });
  }, []);
  const close = useCallback(() => setState({ isOpen: false, viewId: null }), []);
  const back = useCallback(() => {
    setState((prev) => {
      if (!prev.isOpen) return prev;
      if (prev.viewId !== null) return { isOpen: true, viewId: null };
      return { isOpen: false, viewId: null };
    });
  }, []);

  useEffect(() => {
    const wasOpen = wasOpenRef.current;
    wasOpenRef.current = state.isOpen;
    if (wasOpen && !state.isOpen) {
      const t = triggerRef.current;
      triggerRef.current = null;
      t?.focus?.();
    }
  }, [state.isOpen]);

  useEffect(() => {
    setState((prev) => (prev.isOpen ? { isOpen: false, viewId: null } : prev));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const meta = e.metaKey || e.ctrlKey;
      const isK = e.key === 'k' || e.key === 'K';
      if (!isK) return;
      if (!meta) return;
      e.preventDefault();
      // Toggle: press once to open, press again to close.
      setState((prev) => {
        if (prev.isOpen) {
          return { isOpen: false, viewId: null };
        }
        captureTrigger();
        return { isOpen: true, viewId: null };
      });
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const api = useMemo<CommandCenterApi>(
    () => ({ ...state, open, openView, back, close }),
    [state, open, openView, back, close],
  );

  return <Ctx.Provider value={api}>{children}</Ctx.Provider>;
}
