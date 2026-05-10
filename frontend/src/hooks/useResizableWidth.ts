import { useCallback, useEffect, useRef, useState } from 'react';

type Edge = 'left' | 'right';

/**
 * Mouse-drag-resizable width with localStorage persistence and clamp.
 * `edge` describes which edge of the resized panel the handle sits on:
 *   - "right" (default) — handle on the right; drag right → wider.
 *   - "left"            — handle on the left; drag left → wider.
 *
 * Returns `{width, onResizeStart, dragging}`. Bind `onResizeStart` to
 * the handle's onMouseDown and apply the width to the panel.
 */
export function useResizableWidth({
  storageKey,
  defaultWidth,
  min,
  max,
  edge = 'right',
}: {
  storageKey: string;
  defaultWidth: number;
  min: number;
  max: number;
  edge?: Edge;
}) {
  const [width, setWidth] = useState<number>(() => {
    if (typeof window === 'undefined') return defaultWidth;
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return defaultWidth;
    const n = parseInt(raw, 10);
    if (Number.isNaN(n)) return defaultWidth;
    return Math.min(max, Math.max(min, n));
  });
  const [dragging, setDragging] = useState(false);

  const startX = useRef<number | null>(null);
  const startWidth = useRef<number>(width);
  const widthRef = useRef<number>(width);
  useEffect(() => {
    widthRef.current = width;
  }, [width]);

  const onResizeStart = useCallback(
    (e: React.MouseEvent) => {
      startX.current = e.clientX;
      startWidth.current = widthRef.current;
      setDragging(true);
      e.preventDefault();
    },
    [],
  );

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (startX.current === null) return;
      const delta = e.clientX - startX.current;
      const signed = edge === 'right' ? delta : -delta;
      const next = Math.max(min, Math.min(max, startWidth.current + signed));
      setWidth(next);
    }
    function onUp() {
      if (startX.current !== null) {
        try {
          window.localStorage.setItem(storageKey, String(widthRef.current));
        } catch {
          /* noop */
        }
      }
      startX.current = null;
      setDragging(false);
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [edge, min, max, storageKey]);

  return { width, onResizeStart, dragging };
}
