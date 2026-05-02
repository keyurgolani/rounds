import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronUp, Plus, Star } from 'lucide-react';
import { api } from '../../api/client';
import { slugify } from '../../lib/slug';
import type { Anecdote, BehavioralCategoryLite, BehavioralQuestionLite } from './types';

interface MyAnecdotesPanelProps {
  questionId: string;
  questionCategoryIds: string[];
  categories: BehavioralCategoryLite[];
  questions: BehavioralQuestionLite[];
}

function categoryName(cats: BehavioralCategoryLite[], id: string): string {
  return cats.find((c) => c.id === id)?.name || '';
}

function categoryColor(cats: BehavioralCategoryLite[], id: string): string {
  return cats.find((c) => c.id === id)?.color || '#808080';
}

function formatTime(raw?: string | null): string {
  if (!raw) return 'just now';
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return 'recently';
  const diffMs = Date.now() - d.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function useDebouncedCallback<A extends unknown[]>(
  fn: (...args: A) => void,
  delay = 800
): (...args: A) => void {
  const timer = useRef<number | null>(null);
  return (...args: A) => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => fn(...args), delay);
  };
}

export function MyAnecdotesPanel({
  questionId,
  questionCategoryIds,
  categories,
  questions: _questions,
}: MyAnecdotesPanelProps) {
  const navigate = useNavigate();
  const [anecdotes, setAnecdotes] = useState<Anecdote[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [dirty, setDirty] = useState<Anecdote | null>(null);
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [query, setQuery] = useState('');
  const [librarianOpen, setLibrarianOpen] = useState(false);
  const [mode, setMode] = useState<'description' | 'star' | 'both'>('both');

  useEffect(() => {
    api
      .get<Anecdote[]>('/api/anecdotes')
      .then((list) => {
        setAnecdotes(list);
        const linked = list.find((a) => a.linked_question_ids.includes(questionId));
        setSelectedId((linked ?? list[0])?.id ?? null);
      })
      .finally(() => setLoading(false));
  }, [questionId]);

  useEffect(() => {
    setMode('both');
  }, [selectedId]);

  const linked = useMemo(
    () => anecdotes.filter((a) => a.linked_question_ids.includes(questionId)),
    [anecdotes, questionId]
  );

  const libraryCandidates = useMemo(() => {
    const linkedSet = new Set(linked.map((a) => a.id));
    const q = query.trim().toLowerCase();
    return anecdotes
      .filter((a) => !linkedSet.has(a.id))
      .filter((a) => !q || a.title.toLowerCase().includes(q))
      .sort((a, b) => {
        const ma = a.category_ids.filter((c) => questionCategoryIds.includes(c)).length;
        const mb = b.category_ids.filter((c) => questionCategoryIds.includes(c)).length;
        if (mb !== ma) return mb - ma;
        return (b.updated_at ?? '').localeCompare(a.updated_at ?? '');
      });
  }, [anecdotes, linked, query, questionCategoryIds]);

  const selected = useMemo(
    () => anecdotes.find((a) => a.id === selectedId) ?? null,
    [anecdotes, selectedId]
  );

  const persist = useDebouncedCallback(async (a: Anecdote) => {
    setSaving(true);
    try {
      const saved = await api.put<Anecdote>(`/api/anecdotes/${a.id}`, {
        title: a.title,
        description: a.description,
        situation: a.situation,
        task: a.task,
        action: a.action,
        result: a.result,
        category_ids: a.category_ids,
        linked_question_ids: a.linked_question_ids,
        notes: a.notes,
      });
      setAnecdotes((prev) => prev.map((x) => (x.id === saved.id ? saved : x)));
      setLastSavedAt(saved.updated_at ?? new Date().toISOString());
    } finally {
      setSaving(false);
    }
  }, 700);

  function handleField<K extends keyof Anecdote>(key: K, value: Anecdote[K]) {
    if (!selected) return;
    const next = { ...selected, [key]: value };
    setDirty(next);
    setAnecdotes((prev) => prev.map((x) => (x.id === next.id ? next : x)));
    persist(next);
  }

  async function linkAnecdote(a: Anecdote) {
    setLibrarianOpen(false);
    setQuery('');
    const updated = await api.put<Anecdote>(`/api/anecdotes/${a.id}`, {
      title: a.title,
      description: a.description,
      situation: a.situation,
      task: a.task,
      action: a.action,
      result: a.result,
      category_ids: a.category_ids,
      linked_question_ids: [...a.linked_question_ids, questionId],
      notes: a.notes,
    });
    setAnecdotes((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    setSelectedId(updated.id);
  }

  async function unlinkSelected() {
    if (!selected) return;
    const updated = await api.put<Anecdote>(`/api/anecdotes/${selected.id}`, {
      title: selected.title,
      description: selected.description,
      situation: selected.situation,
      task: selected.task,
      action: selected.action,
      result: selected.result,
      category_ids: selected.category_ids,
      linked_question_ids: selected.linked_question_ids.filter((id) => id !== questionId),
      notes: selected.notes,
    });
    setAnecdotes((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    const remaining = linked.filter((a) => a.id !== updated.id);
    setSelectedId(remaining[0]?.id ?? null);
  }

  void dirty;

  const savedLabel = lastSavedAt
    ? `saved · ${formatTime(lastSavedAt)}`
    : selected?.updated_at
      ? `saved · ${formatTime(selected.updated_at)}`
      : 'unsaved';

  return (
    <div
      className="grid gap-4 md:gap-6 grid-cols-1 md:[grid-template-columns:280px_minmax(0,1fr)]"
      style={{ minHeight: 0 }}
    >
      <aside className="flex flex-col gap-4">
        <div className="eyebrow">Notebook</div>

        <div className="flex flex-col gap-1.5">
          {loading ? (
            <div style={{ fontSize: 12, color: 'var(--text-4)' }}>Loading…</div>
          ) : linked.length === 0 ? (
            <div
              className="card p-3"
              style={{ fontSize: 12.5, color: 'var(--text-3)', lineHeight: 1.5 }}
            >
              No anecdotes linked yet. Link one from your library or start fresh.
            </div>
          ) : (
            linked.map((a) => {
              const active = a.id === selectedId;
              return (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => setSelectedId(a.id)}
                  className="text-left transition-colors"
                  style={{
                    padding: 12,
                    border: 0,
                    borderRadius: 6,
                    background: active ? 'var(--bg-elev)' : 'transparent',
                    boxShadow: active ? '0 0 0 1px var(--border)' : 'none',
                    cursor: 'pointer',
                  }}
                >
                  <div
                    className="display-italic"
                    style={{ fontSize: 16, fontWeight: 400, color: 'var(--text)' }}
                  >
                    {a.title}
                  </div>
                  <div
                    className="mono"
                    style={{ fontSize: 10, color: 'var(--text-4)', marginTop: 4 }}
                  >
                    {a.linked_question_ids.length} linked · {formatTime(a.updated_at)}
                  </div>
                </button>
              );
            })
          )}

          <button
            type="button"
            onClick={() => {
              const q = _questions.find((x) => x.id === questionId);
              const ref = q ? slugify(q.title) || String(questionId) : String(questionId);
              navigate(`/behavioral/anecdotes/new?question=${ref}`);
            }}
            className="inline-flex items-center gap-1.5 text-left"
            style={{
              padding: 12,
              border: '1px dashed var(--border-strong)',
              background: 'transparent',
              borderRadius: 6,
              color: 'var(--text-3)',
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            <Plus size={13} strokeWidth={1.7} />
            New anecdote
          </button>
        </div>

        {libraryCandidates.length > 0 && (
          <div className="mt-2">
            <button
              type="button"
              onClick={() => setLibrarianOpen((v) => !v)}
              className="mono uppercase inline-flex items-center gap-1"
              style={{
                fontSize: 10.5,
                color: 'var(--text-3)',
                letterSpacing: '0.12em',
                background: 'transparent',
                border: 0,
                cursor: 'pointer',
                padding: 0,
              }}
            >
              {librarianOpen ? 'Hide library' : 'Link from library'}
              {librarianOpen ? (
                <ChevronUp size={12} strokeWidth={1.8} />
              ) : (
                <ChevronDown size={12} strokeWidth={1.8} />
              )}
            </button>

            {librarianOpen && (
              <div className="mt-2 flex flex-col gap-1.5">
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search your library…"
                  style={{
                    padding: '7px 10px',
                    background: 'var(--bg)',
                    boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                    borderRadius: 6,
                    border: 0,
                    fontSize: 12,
                    color: 'var(--text)',
                    outline: 'none',
                  }}
                />
                <div
                  className="flex flex-col gap-1"
                  style={{ maxHeight: 220, overflowY: 'auto' }}
                >
                  {libraryCandidates.slice(0, 12).map((a) => {
                    const overlap = a.category_ids.filter((c) =>
                      questionCategoryIds.includes(c)
                    ).length;
                    return (
                      <button
                        key={a.id}
                        type="button"
                        onClick={() => linkAnecdote(a)}
                        className="text-left"
                        style={{
                          padding: 10,
                          border: 0,
                          borderRadius: 6,
                          background: 'transparent',
                          boxShadow: 'inset 0 0 0 1px var(--border)',
                          cursor: 'pointer',
                        }}
                      >
                        <div
                          className="flex items-center gap-1.5"
                          style={{ fontSize: 12.5, fontWeight: 500, color: 'var(--text)' }}
                        >
                          {overlap > 0 && (
                            <span
                              title={`${overlap} category match`}
                              style={{ color: 'var(--ochre)', display: 'inline-flex' }}
                            >
                              <Star size={11} fill="var(--ochre)" strokeWidth={0} />
                            </span>
                          )}
                          {a.title}
                        </div>
                        <div
                          style={{
                            fontSize: 11,
                            color: 'var(--text-4)',
                            marginTop: 2,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {a.situation}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </aside>

      <div>
        {!selected ? (
          <div
            className="card p-10 text-center"
            style={{ background: 'var(--bg-elev)', color: 'var(--text-3)' }}
          >
            <div
              className="display-italic mb-2"
              style={{ fontSize: 24, fontWeight: 400, color: 'var(--text)' }}
            >
              No anecdote selected
            </div>
            <p style={{ fontSize: 13, lineHeight: 1.55, maxWidth: 360, margin: '0 auto' }}>
              Pick one from your notebook on the left, link one from your library, or write a new
              STAR story for this question.
            </p>
          </div>
        ) : (
          <>
            <div className="flex justify-between items-center mb-2.5">
              <input
                value={selected.title}
                onChange={(e) => handleField('title', e.target.value)}
                style={{
                  fontFamily: 'var(--font-display)',
                  fontStyle: 'italic',
                  fontSize: 32,
                  fontWeight: 400,
                  lineHeight: 1.1,
                  border: 0,
                  background: 'transparent',
                  color: 'var(--text)',
                  padding: 0,
                  width: '100%',
                  letterSpacing: '-0.02em',
                  outline: 'none',
                }}
              />
              <div
                className="mono whitespace-nowrap"
                style={{ fontSize: 10.5, color: 'var(--text-4)', marginLeft: 12 }}
              >
                {saving ? 'saving…' : savedLabel}
              </div>
            </div>

            <div className="flex items-center gap-3 mb-5">
              <div
                className="mono uppercase"
                style={{
                  fontSize: 10.5,
                  color: 'var(--text-4)',
                  letterSpacing: '0.08em',
                }}
              >
                Linked to this question
              </div>
              <div className="flex flex-wrap gap-1.5">
                {selected.category_ids.map((cid) => (
                  <span
                    key={cid}
                    className="pill"
                    style={{
                      background: 'transparent',
                      color: categoryColor(categories, cid),
                      boxShadow: `inset 0 0 0 1px ${categoryColor(categories, cid)}`,
                    }}
                  >
                    {categoryName(categories, cid)}
                  </span>
                ))}
              </div>
              <button
                type="button"
                onClick={unlinkSelected}
                className="mono uppercase ml-auto"
                style={{
                  fontSize: 10.5,
                  color: 'var(--plum)',
                  letterSpacing: '0.1em',
                  background: 'transparent',
                  border: 0,
                  cursor: 'pointer',
                  padding: 0,
                }}
              >
                Unlink
              </button>
            </div>

            <div className="flex gap-1 mb-4">
              {(['description', 'star', 'both'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  style={{
                    padding: '6px 14px',
                    borderRadius: 'var(--radius)',
                    border: 0,
                    background: mode === m ? 'var(--ink, var(--text))' : 'var(--bg-sunken)',
                    color: mode === m ? 'var(--paper, var(--bg-elev))' : 'var(--text-3)',
                    fontSize: 12.5,
                    fontWeight: mode === m ? 600 : 400,
                    cursor: 'pointer',
                    boxShadow: mode === m ? 'none' : 'inset 0 0 0 1px var(--border-strong)',
                    transition: 'background 0.15s, color 0.15s',
                    textTransform: 'capitalize',
                  }}
                >
                  {m === 'star' ? 'STAR' : m}
                </button>
              ))}
            </div>

            {(mode === 'description' || mode === 'both') && (
              <div className={mode === 'both' ? 'mb-3.5' : ''}>
                <DescriptionField
                  value={selected.description ?? ''}
                  onChange={(v) => handleField('description', v)}
                />
              </div>
            )}
            {(mode === 'star' || mode === 'both') && (
              <div className="grid gap-3.5 grid-cols-1 sm:grid-cols-2">
                <StarField
                  label="Situation"
                  rows={3}
                  value={selected.situation}
                  onChange={(v) => handleField('situation', v)}
                />
                <StarField
                  label="Task"
                  rows={2}
                  value={selected.task}
                  onChange={(v) => handleField('task', v)}
                />
                <StarField
                  label="Action"
                  rows={5}
                  fullWidth
                  value={selected.action}
                  onChange={(v) => handleField('action', v)}
                />
                <StarField
                  label="Result"
                  rows={3}
                  fullWidth
                  value={selected.result}
                  onChange={(v) => handleField('result', v)}
                />
              </div>
            )}

            <CoachTip />
          </>
        )}
      </div>

    </div>
  );
}

function StarField({
  label,
  rows,
  value,
  onChange,
  fullWidth,
}: {
  label: string;
  rows: number;
  value: string;
  onChange: (v: string) => void;
  fullWidth?: boolean;
}) {
  return (
    <div
      className="card"
      style={{ padding: 16, gridColumn: fullWidth ? 'span 2' : 'auto' }}
    >
      <div
        className="eyebrow mb-2.5"
        style={{ color: 'var(--accent)' }}
      >
        {label}
      </div>
      <textarea
        rows={rows}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`What was the ${label.toLowerCase()}?`}
        style={{
          width: '100%',
          border: 0,
          background: 'transparent',
          color: 'var(--text-2)',
          fontSize: 13.5,
          lineHeight: 1.6,
          resize: 'none',
          padding: 0,
          outline: 'none',
          fontFamily: 'inherit',
        }}
      />
    </div>
  );
}

function DescriptionField({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <div className="eyebrow mb-2.5" style={{ color: 'var(--accent)' }}>
        Description
      </div>
      <textarea
        rows={8}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="A short version of the story in your own words."
        style={{
          width: '100%',
          border: 0,
          background: 'transparent',
          color: 'var(--text-2)',
          fontSize: 13.5,
          lineHeight: 1.6,
          resize: 'none',
          padding: 0,
          outline: 'none',
          fontFamily: 'inherit',
        }}
      />
    </div>
  );
}

function CoachTip() {
  return (
    <div
      className="flex items-center gap-3.5 mt-5"
      style={{
        padding: 16,
        borderRadius: 'var(--radius)',
        background: 'var(--bg-sunken)',
      }}
    >
      <div
        className="flex items-center justify-center flex-shrink-0"
        style={{
          width: 36,
          height: 36,
          borderRadius: 999,
          background: 'var(--accent-soft)',
        }}
      >
        <span
          style={{
            fontFamily: 'var(--font-display)',
            fontStyle: 'italic',
            fontSize: 18,
            color: 'var(--accent)',
          }}
        >
          R
        </span>
      </div>
      <div style={{ fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.55 }}>
        <strong style={{ color: 'var(--text)' }}>Coach tip.</strong> Your Result could hit harder.
        What metric changed, by how much, and within what window?
      </div>
    </div>
  );
}
