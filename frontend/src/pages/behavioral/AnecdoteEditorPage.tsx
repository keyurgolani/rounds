import { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../../api/client';
import { slugify } from '../../lib/slug';
import AppHeader from '../../components/shell/AppHeader';
import PageShell from '../../components/shell/PageShell';
import type { Anecdote, BehavioralCategoryLite, BehavioralQuestionLite } from './types';

type Mode = 'description' | 'star' | 'both';

const inputStyle: React.CSSProperties = {
  padding: '10px 12px',
  background: 'var(--bg)',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
  borderRadius: 'var(--radius)',
  border: 0,
  fontSize: 14,
  color: 'var(--text)',
  outline: 'none',
  fontFamily: 'inherit',
  width: '100%',
};

const primaryBtn: React.CSSProperties = {
  padding: '9px 16px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'var(--accent)',
  color: 'var(--bg-elev)',
  fontSize: 13,
  fontWeight: 500,
  cursor: 'pointer',
};

const secondaryBtn: React.CSSProperties = {
  padding: '9px 16px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'var(--bg-sunken)',
  color: 'var(--text-2)',
  fontSize: 13,
  fontWeight: 500,
  cursor: 'pointer',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
};

const dangerBtn: React.CSSProperties = {
  padding: '9px 16px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'transparent',
  color: 'var(--plum)',
  fontSize: 13,
  fontWeight: 500,
  cursor: 'pointer',
};

function ModeButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: '6px 14px',
        borderRadius: 'var(--radius)',
        border: 0,
        background: active ? 'var(--ink, var(--text))' : 'var(--bg-sunken)',
        color: active ? 'var(--paper, var(--bg-elev))' : 'var(--text-3)',
        fontSize: 12.5,
        fontWeight: active ? 600 : 400,
        cursor: 'pointer',
        boxShadow: active ? 'none' : 'inset 0 0 0 1px var(--border-strong)',
        transition: 'background 0.15s, color 0.15s',
      }}
    >
      {children}
    </button>
  );
}

const empty = {
  title: '',
  description: '',
  situation: '',
  task: '',
  action: '',
  result: '',
  category_ids: [] as string[],
  linked_question_ids: [] as string[],
  notes: '',
};

export function AnecdoteEditorPage() {
  const { slug } = useParams<{ slug?: string }>();
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const preQuestion = search.get('question');
  const isEdit = Boolean(slug);

  const [form, setForm] = useState({ ...empty });
  const [existingId, setExistingId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>('both');
  const [categories, setCategories] = useState<BehavioralCategoryLite[]>([]);
  const [questions, setQuestions] = useState<BehavioralQuestionLite[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<BehavioralCategoryLite[]>('/api/behavioral-categories').catch(() => []),
      api.get<BehavioralQuestionLite[]>('/api/behavioral').catch(() => []),
      slug
        ? (async () => {
            const anecdotes = await api.get<Anecdote[]>('/api/anecdotes').catch(() => []);
            const byTitle = anecdotes.find((a) => slugify(a.title) === slug);
            if (byTitle) return byTitle;
            const byId = anecdotes.find((a) => a.id === slug);
            return byId ?? null;
          })()
        : Promise.resolve(null),
    ]).then(([cats, qs, existing]) => {
      setCategories(cats ?? []);
      setQuestions(qs ?? []);
      if (existing) {
        setExistingId(existing.id);
        setForm({
          title: existing.title,
          description: existing.description ?? '',
          situation: existing.situation ?? '',
          task: existing.task ?? '',
          action: existing.action ?? '',
          result: existing.result ?? '',
          category_ids: existing.category_ids ?? [],
          linked_question_ids: existing.linked_question_ids ?? [],
          notes: existing.notes ?? '',
        });
      } else if (preQuestion) {
        const matched = (qs ?? []).find(
          (q) => slugify(q.title) === slugify(preQuestion)
        );
        if (matched) {
          setForm((f) => ({ ...f, linked_question_ids: [matched.id] }));
        }
      }
      setLoading(false);
    });
  }, [slug, preQuestion]);

  const toggleCat = (cid: string) => {
    setForm((f) => ({
      ...f,
      category_ids: f.category_ids.includes(cid)
        ? f.category_ids.filter((c) => c !== cid)
        : [...f.category_ids, cid],
    }));
  };

  const toggleQ = (qid: string) => {
    setForm((f) => ({
      ...f,
      linked_question_ids: f.linked_question_ids.includes(qid)
        ? f.linked_question_ids.filter((q) => q !== qid)
        : [...f.linked_question_ids, qid],
    }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim()) {
      setError('Title is required.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const body = {
        title: form.title,
        description: form.description,
        situation: form.situation,
        task: form.task,
        action: form.action,
        result: form.result,
        category_ids: form.category_ids,
        linked_question_ids: form.linked_question_ids,
        notes: form.notes,
      };
      if (existingId) {
        await api.put<Anecdote>(`/api/anecdotes/${existingId}`, body);
      } else {
        await api.post<Anecdote>('/api/anecdotes', body);
      }
      navigate(-1);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    navigate(-1);
  };

  const handleDelete = async () => {
    if (!existingId) return;
    if (!confirm('Delete this anecdote? This cannot be undone.')) return;
    setSaving(true);
    try {
      await api.del(`/api/anecdotes/${existingId}`);
      navigate(-1);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageShell header={null}>
        <div className="px-8 py-6" style={{ color: 'var(--text-3)', fontSize: 13 }}>
          Loading…
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell
      header={
        <AppHeader
          eyebrow={isEdit ? 'Behavioral · Edit anecdote' : 'Behavioral · New anecdote'}
          title={isEdit ? 'Edit anecdote' : 'New anecdote'}
          description="Capture the story once. Pull it back up whenever an interviewer prompts for it."
        />
      }
    >
      <form
        onSubmit={handleSave}
        className="px-5 sm:px-8 py-6"
        style={{ paddingBottom: 'calc(var(--fab-safe-area, 96px))' }}
      >
        <div className="card p-6 space-y-5">
          {/* Title */}
          <label className="flex flex-col gap-1">
            <span className="eyebrow">Title</span>
            <input
              aria-label="Title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              style={inputStyle}
            />
          </label>

          {/* Mode toggle */}
          <div className="flex flex-col gap-2">
            <span className="eyebrow">Format</span>
            <div className="flex gap-1">
              <ModeButton active={mode === 'description'} onClick={() => setMode('description')}>
                Description
              </ModeButton>
              <ModeButton active={mode === 'star'} onClick={() => setMode('star')}>
                STAR
              </ModeButton>
              <ModeButton active={mode === 'both'} onClick={() => setMode('both')}>
                Both
              </ModeButton>
            </div>
          </div>

          {/* Description, STAR, or both */}
          {(mode === 'description' || mode === 'both') && (
            <label className="flex flex-col gap-1">
              <span className="eyebrow">Description</span>
              <textarea
                aria-label="Description"
                rows={6}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                style={{ ...inputStyle, resize: 'vertical' }}
              />
            </label>
          )}
          {(mode === 'star' || mode === 'both') && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(['situation', 'task', 'action', 'result'] as const).map((k) => (
                <label
                  key={k}
                  className="flex flex-col gap-1"
                  style={k === 'action' ? { gridColumn: '1 / -1' } : undefined}
                >
                  <span className="eyebrow">{k}</span>
                  <textarea
                    aria-label={k.charAt(0).toUpperCase() + k.slice(1)}
                    rows={k === 'action' ? 5 : 3}
                    value={form[k]}
                    onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                    style={{ ...inputStyle, resize: 'vertical' }}
                  />
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="card p-6 mt-5 space-y-5">
          {/* Categories */}
          <div className="flex flex-col gap-2">
            <span className="eyebrow">Categories</span>
            <div className="flex flex-wrap gap-1.5">
              {categories.map((c) => {
                const on = form.category_ids.includes(c.id);
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => toggleCat(c.id)}
                    className="pill transition-colors"
                    style={{
                      background: on ? c.color : 'transparent',
                      color: on ? 'var(--paper, #fff)' : c.color,
                      boxShadow: on ? 'none' : `inset 0 0 0 1px var(--border-strong)`,
                    }}
                  >
                    {c.name}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Linked questions */}
          <div className="flex flex-col gap-2">
            <span className="eyebrow">Linked questions</span>
            <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto">
              {questions.map((q) => {
                const on = form.linked_question_ids.includes(q.id);
                return (
                  <button
                    key={q.id}
                    type="button"
                    onClick={() => toggleQ(q.id)}
                    className="pill transition-colors text-left"
                    style={{
                      background: on ? 'var(--ink, var(--text))' : 'var(--bg-sunken)',
                      color: on ? 'var(--paper, var(--bg-elev))' : 'var(--text-3)',
                      boxShadow: on ? 'none' : 'inset 0 0 0 1px var(--border-strong)',
                    }}
                  >
                    {q.title}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Notes */}
          <label className="flex flex-col gap-1">
            <span className="eyebrow">Notes</span>
            <textarea
              aria-label="Notes"
              rows={3}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              style={{ ...inputStyle, resize: 'vertical' }}
            />
          </label>
        </div>

        {error && (
          <div className="mt-4" style={{ fontSize: 13, color: 'var(--plum)' }}>
            {error}
          </div>
        )}

        <div className="mt-6 flex items-center justify-between">
          {isEdit ? (
            <button type="button" onClick={handleDelete} style={dangerBtn} disabled={saving}>
              Delete anecdote
            </button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <button type="button" onClick={handleCancel} style={secondaryBtn}>
              Cancel
            </button>
            <button type="submit" style={primaryBtn} disabled={saving}>
              {saving ? 'Saving…' : 'Save anecdote'}
            </button>
          </div>
        </div>
      </form>
    </PageShell>
  );
}
