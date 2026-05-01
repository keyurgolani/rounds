import { useEffect, useMemo, useRef, useState } from 'react';

type Options = {
  initial?: number;
  step?: number;
};

// Infinite-scroll renderer for a fully-fetched array. Returns the slice
// to render plus a sentinel ref to attach to the row that, when visible,
// reveals the next chunk.
//
// We render the array as it grows (filter/sort changes upstream) — the
// `items` reference is the cache key, so any new array resets the
// visible window back to `initial`.
export function useInfiniteList<T>(items: T[], options: Options = {}) {
  const { initial = 30, step = 30 } = options;
  const [visible, setVisible] = useState(initial);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setVisible(initial);
  }, [items, initial]);

  const slice = useMemo(() => items.slice(0, visible), [items, visible]);
  const hasMore = visible < items.length;

  useEffect(() => {
    const node = sentinelRef.current;
    if (!node || !hasMore) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible((v) => Math.min(v + step, items.length));
            break;
          }
        }
      },
      { rootMargin: '400px 0px' },
    );
    io.observe(node);
    return () => io.disconnect();
  }, [hasMore, items.length, step]);

  return { slice, sentinelRef, hasMore, visible };
}
