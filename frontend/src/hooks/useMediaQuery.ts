// Whether a media query matches, kept current as the window changes, the
// way AppHeader follows its compact width.

import { useEffect, useState } from 'react';

/** Phone widths, where a practice page's side rail leaves its center
 *  column too narrow to read a runner notice in. AppHeader turns compact
 *  at the same width. */
export const NARROW_SCREEN_QUERY = '(max-width: 640px)';

function current(query: string): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia(query).matches
    : false;
}

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => current(query));

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
    const mq = window.matchMedia(query);
    setMatches(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setMatches(e.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [query]);

  return matches;
}
