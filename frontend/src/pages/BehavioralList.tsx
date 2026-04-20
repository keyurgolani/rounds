import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { slugify } from '../lib/slug';
import PageHeader from '../components/shell/PageHeader';
import { LinkableCard } from './behavioral/LinkableCard';
import { ConnectorOverlay, type Connector, type Endpoint } from './behavioral/ConnectorOverlay';
import type { Anecdote } from './behavioral/types';

interface BQ {
  id: number;
  title: string;
  question_text: string;
  category_ids: number[];
  tags: string[];
}

interface BC {
  id: number;
  name: string;
  description: string;
  color: string;
  icon: string;
}

type DragState = {
  kind: 'question' | 'anecdote';
  id: number;
  fromX: number;
  fromY: number;
  x: number;
  y: number;
};

type DropTarget = { kind: 'question' | 'anecdote'; id: number };

function findScrollAncestor(el: HTMLElement | null): HTMLElement | null {
  let cur = el?.parentElement ?? null;
  while (cur) {
    const s = getComputedStyle(cur);
    if (/(auto|scroll)/.test(s.overflowY)) return cur;
    cur = cur.parentElement;
  }
  return null;
}

export default function BehavioralList() {
  const navigate = useNavigate();
  const [questions, setQuestions] = useState<BQ[]>([]);
  const [categories, setCategories] = useState<BC[]>([]);
  const [anecdotes, setAnecdotes] = useState<Anecdote[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeCat, setActiveCat] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<BQ[]>('/api/behavioral'),
      api.get<BC[]>('/api/behavioral-categories'),
      api.get<Anecdote[]>('/api/anecdotes'),
    ])
      .then(([qs, cats, ans]) => {
        setQuestions(qs);
        setCategories(cats);
        setAnecdotes(ans);
      })
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(
    () => (activeCat ? questions.filter((q) => q.category_ids.includes(activeCat)) : questions),
    [questions, activeCat]
  );

  const links = useMemo(() => {
    const s = new Set<string>();
    anecdotes.forEach((a) =>
      a.linked_question_ids.forEach((qid) => s.add(`q${qid}-a${a.id}`))
    );
    return s;
  }, [anecdotes]);

  const isLinked = useCallback((qId: number, aId: number) => links.has(`q${qId}-a${aId}`), [
    links,
  ]);
  const linksFromQuestion = useCallback(
    (qId: number) => anecdotes.filter((a) => isLinked(qId, a.id)),
    [anecdotes, isLinked]
  );
  const linksFromAnecdote = useCallback(
    (aId: number) => questions.filter((q) => isLinked(q.id, aId)),
    [questions, isLinked]
  );

  const toggleLink = useCallback(
    async (qId: number, aId: number) => {
      const anecdote = anecdotes.find((a) => a.id === aId);
      if (!anecdote) return;
      const linked = anecdote.linked_question_ids.includes(qId);
      const updated = linked
        ? anecdote.linked_question_ids.filter((x) => x !== qId)
        : [...anecdote.linked_question_ids, qId];
      // Optimistic update
      setAnecdotes((prev) =>
        prev.map((a) => (a.id === aId ? { ...a, linked_question_ids: updated } : a))
      );
      try {
        const saved = await api.put<Anecdote>(`/api/anecdotes/${aId}`, {
          title: anecdote.title,
          description: anecdote.description,
          situation: anecdote.situation,
          task: anecdote.task,
          action: anecdote.action,
          result: anecdote.result,
          category_ids: anecdote.category_ids,
          linked_question_ids: updated,
          notes: anecdote.notes,
        });
        setAnecdotes((prev) => prev.map((a) => (a.id === aId ? saved : a)));
      } catch {
        // Revert on failure
        setAnecdotes((prev) =>
          prev.map((a) =>
            a.id === aId ? { ...a, linked_question_ids: anecdote.linked_question_ids } : a
          )
        );
      }
    },
    [anecdotes]
  );

  const questionRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const anecdoteRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [hovered, setHovered] = useState<{ kind: 'question' | 'anecdote'; id: number } | null>(
    null
  );
  const [drag, setDrag] = useState<DragState | null>(null);
  const [dropTarget, setDropTarget] = useState<DropTarget | null>(null);
  const [, forceTick] = useReducer((n: number) => n + 1, 0);

  useEffect(() => {
    const handler = () => forceTick();
    window.addEventListener('resize', handler);
    const scrollEl = findScrollAncestor(containerRef.current);
    scrollEl?.addEventListener('scroll', handler);
    const id = requestAnimationFrame(handler);
    return () => {
      window.removeEventListener('resize', handler);
      scrollEl?.removeEventListener('scroll', handler);
      cancelAnimationFrame(id);
    };
  }, [filtered.length, anecdotes.length]);

  const edgePoint = useCallback(
    (el: HTMLElement | null, side: 'right' | 'left'): Endpoint | null => {
      if (!el || !containerRef.current) return null;
      const a = el.getBoundingClientRect();
      const b = containerRef.current.getBoundingClientRect();
      return {
        x: side === 'right' ? a.right - b.left : a.left - b.left,
        y: a.top - b.top + a.height / 2,
      };
    },
    []
  );

  const hitTestCard = useCallback((clientX: number, clientY: number): DropTarget | null => {
    const test = (
      kind: 'question' | 'anecdote',
      refs: Record<number, HTMLDivElement | null>
    ): DropTarget | null => {
      for (const key in refs) {
        const el = refs[Number(key)];
        if (!el) continue;
        const r = el.getBoundingClientRect();
        if (clientX >= r.left && clientX <= r.right && clientY >= r.top && clientY <= r.bottom) {
          return { kind, id: Number(key) };
        }
      }
      return null;
    };
    return test('question', questionRefs.current) ?? test('anecdote', anecdoteRefs.current);
  }, []);

  const beginDrag = useCallback(
    (kind: 'question' | 'anecdote', id: number, e: ReactPointerEvent<HTMLSpanElement>) => {
      e.preventDefault();
      e.stopPropagation();
      const el =
        kind === 'question' ? questionRefs.current[id] : anecdoteRefs.current[id];
      const pt = edgePoint(el, kind === 'question' ? 'right' : 'left');
      const container = containerRef.current;
      if (!pt || !container) return;
      const rect = container.getBoundingClientRect();
      setDrag({
        kind,
        id,
        fromX: pt.x,
        fromY: pt.y,
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
    },
    [edgePoint]
  );

  useEffect(() => {
    if (!drag) return;
    const handleMove = (e: PointerEvent) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      setDrag((d) => (d ? { ...d, x, y } : d));
      const hit = hitTestCard(e.clientX, e.clientY);
      setDropTarget((prev) => {
        if (!hit) return null;
        if (prev && prev.kind === hit.kind && prev.id === hit.id) return prev;
        return hit;
      });
    };
    const handleUp = (e: PointerEvent) => {
      const hit = hitTestCard(e.clientX, e.clientY);
      if (drag && hit && hit.kind !== drag.kind) {
        const qId = drag.kind === 'question' ? drag.id : hit.id;
        const aId = drag.kind === 'anecdote' ? drag.id : hit.id;
        void toggleLink(qId, aId);
      }
      setDrag(null);
      setDropTarget(null);
    };
    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
    return () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };
  }, [drag, hitTestCard, toggleLink]);

  const isLinkActive = useCallback(
    (qId: number, aId: number) => {
      if (!hovered) return false;
      if (hovered.kind === 'question' && hovered.id === qId) return true;
      if (hovered.kind === 'anecdote' && hovered.id === aId) return true;
      return false;
    },
    [hovered]
  );

  const isCardActive = useCallback(
    (kind: 'question' | 'anecdote', id: number) => {
      if (!hovered) return false;
      if (hovered.kind === kind && hovered.id === id) return true;
      if (hovered.kind === 'question' && kind === 'anecdote') return isLinked(hovered.id, id);
      if (hovered.kind === 'anecdote' && kind === 'question') return isLinked(id, hovered.id);
      return false;
    },
    [hovered, isLinked]
  );

  const isCardDimmed = useCallback(
    (kind: 'question' | 'anecdote', id: number) => {
      if (!hovered) return false;
      return !isCardActive(kind, id);
    },
    [hovered, isCardActive]
  );

  const connectors: Connector[] = useMemo(() => {
    if (!containerRef.current) return [];
    const b = containerRef.current.getBoundingClientRect();
    const result: Connector[] = [];
    anecdotes.forEach((a) => {
      filtered.forEach((q) => {
        if (!isLinked(q.id, a.id)) return;
        const qEl = questionRefs.current[q.id];
        const aEl = anecdoteRefs.current[a.id];
        if (!qEl || !aEl) return;
        const qr = qEl.getBoundingClientRect();
        const ar = aEl.getBoundingClientRect();
        result.push({
          key: `q${q.id}-a${a.id}`,
          from: { x: qr.right - b.left, y: qr.top - b.top + qr.height / 2 },
          to: { x: ar.left - b.left, y: ar.top - b.top + ar.height / 2 },
          active: isLinkActive(q.id, a.id),
        });
      });
    });
    return result;
  }, [anecdotes, filtered, isLinked, isLinkActive]);

  return (
    <div className="h-full overflow-y-auto" data-scroll-root>
      <PageHeader
        eyebrow="Track 03 · Behavioral"
        title="Behavioral"
        subtitle="Not questions to memorize — stories to own. Drag a question onto an anecdote (or the reverse) to link them. Hover to see the web."
      />

      <div className="mx-auto px-8 py-5" style={{ maxWidth: 1280 }}>
        <div className="flex gap-2 flex-wrap mb-5">
          <CatChip
            active={activeCat === null}
            color="var(--text)"
            label="All"
            onClick={() => setActiveCat(null)}
          />
          {categories.map((c) => (
            <CatChip
              key={c.id}
              active={activeCat === c.id}
              color={c.color}
              label={c.name}
              onClick={() => setActiveCat(activeCat === c.id ? null : c.id)}
            />
          ))}
        </div>

        {loading ? (
          <div className="text-center py-16" style={{ color: 'var(--text-3)' }}>
            Loading…
          </div>
        ) : (
          <div
            ref={containerRef}
            className="grid gap-5"
            style={{
              gridTemplateColumns: '1.5fr 1fr',
              position: 'relative',
            }}
          >
            <ConnectorOverlay
              connectors={connectors}
              drag={drag}
              hasDropTarget={Boolean(dropTarget)}
            />

            <div style={{ position: 'relative', zIndex: 2 }}>
              <div className="eyebrow mb-3">Questions</div>
              <div className="flex flex-col gap-2.5">
                {filtered.map((q, i) => {
                  const linked = linksFromQuestion(q.id);
                  const active = isCardActive('question', q.id);
                  const dimmed = isCardDimmed('question', q.id);
                  const isDrop =
                    drag?.kind === 'anecdote' &&
                    dropTarget?.kind === 'question' &&
                    dropTarget.id === q.id;
                  const isSrc = drag?.kind === 'question' && drag.id === q.id;
                  return (
                    <LinkableCard
                      key={q.id}
                      innerRef={(el) => (questionRefs.current[q.id] = el)}
                      onMouseEnter={() => !drag && setHovered({ kind: 'question', id: q.id })}
                      onMouseLeave={() => !drag && setHovered(null)}
                      onOpen={() => navigate(`/behavioral/question/${slugify(q.title) || q.id}`)}
                      active={active}
                      dimmed={dimmed}
                      isDropTarget={Boolean(isDrop)}
                      isDragSource={Boolean(isSrc)}
                      delay={i * 30}
                      side="right"
                      onBeginDrag={(e) => beginDrag('question', q.id, e)}
                    >
                      <div className="flex gap-1.5 flex-wrap">
                        {q.category_ids.map((cid) => {
                          const c = categories.find((x) => x.id === cid);
                          if (!c) return null;
                          return (
                            <span
                              key={cid}
                              className="pill"
                              style={{
                                background: 'transparent',
                                color: c.color,
                                boxShadow: `inset 0 0 0 1px ${c.color}`,
                              }}
                            >
                              {c.name}
                            </span>
                          );
                        })}
                      </div>
                      <div
                        className="display-italic"
                        style={{ fontSize: 22, lineHeight: 1.2, fontWeight: 400 }}
                      >
                        {q.title}
                      </div>
                      <p
                        style={{
                          margin: 0,
                          fontSize: 12.5,
                          color: 'var(--text-3)',
                          lineHeight: 1.55,
                        }}
                      >
                        {q.question_text}
                      </p>
                      <div
                        className="flex items-center gap-2 pt-1.5"
                        style={{ borderTop: '1px solid var(--border)' }}
                      >
                        <AnecdoteBadge count={linked.length} />
                      </div>
                    </LinkableCard>
                  );
                })}
              </div>
            </div>

            <div style={{ position: 'relative', zIndex: 2 }}>
              <div className="flex items-center justify-between mb-3">
                <div className="eyebrow">Your notebook</div>
                <button
                  type="button"
                  onClick={() => navigate('/behavioral/anecdotes/new')}
                  style={{
                    padding: '4px 10px',
                    border: 0,
                    background: 'var(--accent)',
                    color: 'var(--bg-elev)',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 500,
                    cursor: 'pointer',
                  }}
                >
                  + new
                </button>
              </div>
              <div className="flex flex-col gap-2.5">
                {anecdotes.map((a, i) => {
                  const linked = linksFromAnecdote(a.id);
                  const active = isCardActive('anecdote', a.id);
                  const dimmed = isCardDimmed('anecdote', a.id);
                  const isDrop =
                    drag?.kind === 'question' &&
                    dropTarget?.kind === 'anecdote' &&
                    dropTarget.id === a.id;
                  const isSrc = drag?.kind === 'anecdote' && drag.id === a.id;
                  return (
                    <LinkableCard
                      key={a.id}
                      innerRef={(el) => (anecdoteRefs.current[a.id] = el)}
                      onMouseEnter={() => !drag && setHovered({ kind: 'anecdote', id: a.id })}
                      onMouseLeave={() => !drag && setHovered(null)}
                      onOpen={() => navigate(`/behavioral/anecdotes/${slugify(a.title) || a.id}/edit`)}
                      active={active}
                      dimmed={dimmed}
                      isDropTarget={Boolean(isDrop)}
                      isDragSource={Boolean(isSrc)}
                      delay={i * 30}
                      side="left"
                      onBeginDrag={(e) => beginDrag('anecdote', a.id, e)}
                      compact
                    >
                      <div
                        className="display-italic"
                        style={{ fontSize: 18, lineHeight: 1.2, fontWeight: 400 }}
                      >
                        {a.title}
                      </div>
                      <p
                        style={{
                          margin: '6px 0 0',
                          fontSize: 12,
                          color: 'var(--text-3)',
                          lineHeight: 1.5,
                        }}
                      >
                        {a.situation.slice(0, 90)}
                        {a.situation.length > 90 ? '…' : ''}
                      </p>
                      <div
                        className="mono"
                        style={{ marginTop: 10, fontSize: 10, color: 'var(--text-4)' }}
                      >
                        {linked.length} linked · {a.updated_at ? formatShort(a.updated_at) : 'new'}
                      </div>
                    </LinkableCard>
                  );
                })}
                <button
                  type="button"
                  onClick={() => navigate('/behavioral/anecdotes/new')}
                  style={{
                    padding: 16,
                    border: '1px dashed var(--border-strong)',
                    background: 'transparent',
                    borderRadius: 'var(--radius)',
                    color: 'var(--text-3)',
                    fontSize: 12,
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <span
                    style={{
                      fontFamily: 'var(--font-display)',
                      fontStyle: 'italic',
                      marginRight: 6,
                    }}
                  >
                    +
                  </span>
                  Write a new anecdote
                </button>
              </div>
            </div>
          </div>
        )}

        <div
          className="mono flex items-center justify-center gap-6"
          style={{
            fontSize: 10.5,
            color: 'var(--text-4)',
            letterSpacing: '0.08em',
            position: 'sticky',
            bottom: 0,
            background: 'var(--bg)',
            padding: '12px 0',
            marginTop: 12,
            borderTop: '1px solid var(--border)',
            zIndex: 10,
          }}
        >
          <span className="inline-flex items-center gap-2">
            <svg width="28" height="8" aria-hidden="true">
              <path
                d="M0 4 Q 14 -2, 28 4"
                stroke="var(--border-strong)"
                strokeWidth="1"
                fill="none"
              />
            </svg>
            EXISTING LINK
          </span>
          <span className="inline-flex items-center gap-2">
            <svg width="28" height="8" aria-hidden="true">
              <path d="M0 4 Q 14 -2, 28 4" stroke="var(--accent)" strokeWidth="1.5" fill="none" />
            </svg>
            HIGHLIGHTED
          </span>
          <span>DRAG THE · HANDLE TO LINK</span>
        </div>
      </div>

    </div>
  );
}

function CatChip({
  active,
  color,
  label,
  onClick,
}: {
  active: boolean;
  color: string;
  label: string;
  onClick: () => void;
}) {
  const isCssVar = color.includes('var');
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: '5px 12px',
        border: 0,
        borderRadius: 999,
        background: active ? color : 'transparent',
        color: active ? 'var(--bg-elev)' : color,
        boxShadow: active ? 'none' : `inset 0 0 0 1px ${isCssVar ? 'var(--border-strong)' : color}`,
        fontSize: 11.5,
        fontWeight: 500,
        opacity: isCssVar ? 1 : 0.95,
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  );
}

function AnecdoteBadge({ count }: { count: number }) {
  if (count === 0) {
    return (
      <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.08em' }}>
        — no anecdote yet
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="mono"
        style={{
          padding: '1px 7px',
          borderRadius: 999,
          background: 'var(--accent-soft)',
          color: 'var(--accent)',
          fontSize: 10.5,
        }}
      >
        {count} linked
      </span>
      <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
        anecdote{count !== 1 ? 's' : ''}
      </span>
    </span>
  );
}

function formatShort(d: string) {
  const date = new Date(d);
  if (isNaN(date.getTime())) return '';
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
