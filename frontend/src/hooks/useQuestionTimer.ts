import { useCallback, useEffect, useRef, useState } from 'react';
import { pb } from '../lib/pocketbase';
import type { PracticeKind } from './progressApi';

type Row = {
  id: string;
  user: string;
  question_type: PracticeKind;
  question_slug: string;
  accumulated_ms: number;
  started_at: string;
};

type Result = {
  /** Current elapsed time in ms — ticks every 1s while running. */
  displayMs: number;
  /** True iff a started_at is set. */
  running: boolean;
  /** True after the initial PB fetch completes (success or empty). */
  ready: boolean;
  /** Toggle start/pause. Optimistic. */
  toggle: () => void;
  /** Zero everything out. Optimistic. */
  reset: () => void;
};

const COLL = 'question_timers';

function parseStartedAt(s: string): number | null {
  if (!s) return null;
  const t = Date.parse(s);
  return Number.isFinite(t) ? t : null;
}

/**
 * Per-question persistent timer. Reads/writes one row of
 * `question_timers` keyed by (user, kind, id). Display ticks every
 * 1s while running. Toggle/reset are optimistic; on PB error we log
 * and refetch so the local state doesn't drift.
 *
 * `id` is stringified — slug-keyed tracks pass slugs, id-keyed tracks
 * pass numeric ids (matching StatusAction's posture).
 */
export function useQuestionTimer(
  kind: PracticeKind,
  id: string | number | null | undefined,
): Result {
  const slug = id == null ? '' : String(id);
  const [row, setRow] = useState<Row | null>(null);
  const [ready, setReady] = useState(false);
  // Tick state — incremented every 1s while running so the display
  // re-renders. Doesn't store the elapsed time itself; we recompute
  // from row + Date.now() on every render.
  const [, setTick] = useState(0);

  // Load row on (kind, slug) change.
  useEffect(() => {
    if (!slug) {
      setRow(null);
      setReady(true);
      return;
    }
    let cancelled = false;
    setReady(false);
    (async () => {
      try {
        const found = await pb
          .collection(COLL)
          .getFirstListItem<Row>(
            `question_type="${kind}" && question_slug="${slug.replace(/"/g, '\\"')}"`,
          );
        if (!cancelled) setRow(found);
      } catch {
        // No row yet — that's fine. Stays null until first toggle.
        if (!cancelled) setRow(null);
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [kind, slug]);

  // Tick while running.
  const running = !!row && !!row.started_at;
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setTick((v) => v + 1), 1000);
    return () => clearInterval(t);
  }, [running]);

  // Compute display.
  const startedMs = row?.started_at ? parseStartedAt(row.started_at) : null;
  const baseMs = row?.accumulated_ms ?? 0;
  const displayMs =
    startedMs != null ? baseMs + Math.max(0, Date.now() - startedMs) : baseMs;

  // Async write helper (one inflight at a time per slug).
  const writeRef = useRef<Promise<void>>(Promise.resolve());
  const persist = useCallback(
    async (next: Partial<Row>) => {
      const userId = pb.authStore.model?.id;
      if (!userId || !slug) return;
      writeRef.current = writeRef.current.then(async () => {
        try {
          if (row) {
            const updated = await pb.collection(COLL).update<Row>(row.id, next);
            setRow(updated);
          } else {
            const created = await pb.collection(COLL).create<Row>({
              user: userId,
              question_type: kind,
              question_slug: slug,
              accumulated_ms: 0,
              started_at: '',
              ...next,
            });
            setRow(created);
          }
        } catch (e) {
          // eslint-disable-next-line no-console
          console.warn('[question-timer] persist failed:', e);
          // Re-fetch on error so we converge with server truth.
          try {
            const refetched = await pb
              .collection(COLL)
              .getFirstListItem<Row>(
                `question_type="${kind}" && question_slug="${slug.replace(/"/g, '\\"')}"`,
              );
            setRow(refetched);
          } catch {
            setRow(null);
          }
        }
      });
      return writeRef.current;
    },
    [kind, slug, row],
  );

  const toggle = useCallback(() => {
    if (!ready || !slug) return;
    if (running) {
      // Pause: roll started_at into accumulated.
      const elapsed = startedMs != null ? Math.max(0, Date.now() - startedMs) : 0;
      const next = baseMs + elapsed;
      // Optimistic.
      setRow((r) => (r ? { ...r, accumulated_ms: next, started_at: '' } : r));
      void persist({ accumulated_ms: next, started_at: '' });
    } else {
      const nowIso = new Date().toISOString();
      setRow((r) =>
        r ? { ...r, started_at: nowIso } : ({
          id: '', user: '', question_type: kind, question_slug: slug,
          accumulated_ms: 0, started_at: nowIso,
        } as Row),
      );
      void persist({ started_at: nowIso });
    }
  }, [ready, running, slug, kind, startedMs, baseMs, persist]);

  const reset = useCallback(() => {
    if (!ready || !slug) return;
    setRow((r) => (r ? { ...r, accumulated_ms: 0, started_at: '' } : r));
    void persist({ accumulated_ms: 0, started_at: '' });
  }, [ready, slug, persist]);

  return { displayMs, running, ready, toggle, reset };
}
