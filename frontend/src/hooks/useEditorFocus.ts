import { useCallback, useEffect, useState } from 'react';

/**
 * Editor focus mode — collapses the surrounding chrome (problem bar,
 * right rail, etc) so the editor takes the full width of its column.
 * Persisted per-page via localStorage so coming back to a question
 * keeps the user's focus preference. Esc exits focus mode.
 *
 * Pages should use this hook and conditionally render their problem
 * bar / right rail based on `focus`. The AI chat rail (if present)
 * stays available even in focus mode, since the user explicitly asked
 * for that escape valve when concentrating.
 */
export function useEditorFocus(storageKey: string) {
  const [focus, setFocus] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem(storageKey) === 'true';
  });

  const toggle = useCallback(() => {
    setFocus((f) => {
      const next = !f;
      window.localStorage.setItem(storageKey, String(next));
      return next;
    });
  }, [storageKey]);

  useEffect(() => {
    if (!focus) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setFocus(false);
        window.localStorage.setItem(storageKey, 'false');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [focus, storageKey]);

  return { focus, toggle };
}
