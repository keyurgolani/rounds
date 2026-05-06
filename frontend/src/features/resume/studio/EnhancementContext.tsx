// Studio-wide context that any AI improve / optimize call can read
// from to ground its rewrite in the full resume + the most recent
// ATS feedback (rule + AI).
//
// StudioShell wraps the children with <EnhancementProvider> and
// passes the live `resume` value. ATSTab pushes its scoring results
// in via `useEnhancementATS()`. ImproveButton reads everything via
// `useEnhancementContext()`.

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { ResumeData } from '../types';
import type { ImproveATSSnapshot } from '../ai/client';

type ATSPushPayload = {
  ai_suggestions?: string[];
  ai_signals?: ImproveATSSnapshot['ai_signals'];
};

type Ctx = {
  resume: ResumeData | null;
  ats: ImproveATSSnapshot | null;
  setATS: (next: ATSPushPayload | null) => void;
};

const EnhancementCtx = createContext<Ctx>({
  resume: null,
  ats: null,
  setATS: () => {},
});

export function EnhancementProvider({
  resume,
  children,
}: {
  resume: ResumeData;
  children: ReactNode;
}) {
  const [ats, setATSState] = useState<ImproveATSSnapshot | null>(null);

  const setATS = useCallback((next: ATSPushPayload | null) => {
    if (!next) {
      setATSState(null);
      return;
    }
    setATSState({
      ai_suggestions: next.ai_suggestions,
      ai_signals: next.ai_signals,
    });
  }, []);

  const value = useMemo<Ctx>(
    () => ({ resume, ats, setATS }),
    [resume, ats, setATS],
  );
  return <EnhancementCtx.Provider value={value}>{children}</EnhancementCtx.Provider>;
}

export function useEnhancementContext(): Ctx {
  return useContext(EnhancementCtx);
}
