import { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Sparkles, X } from 'lucide-react';
import {
  listBehavioralCategories,
  listBehavioralQuestions,
} from '../../content/api';
import {
  createAnecdote,
  deleteAnecdote,
  listAnecdotes,
  updateAnecdote,
} from './anecdotesApi';
import { slugify } from '../../lib/slug';
import AppHeader from '../../components/shell/AppHeader';
import PageShell from '../../components/shell/PageShell';
import { createBullet } from '../../features/resume/api';
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
  const [anecdotes, setAnecdotes] = useState<Anecdote[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      listBehavioralCategories<BehavioralCategoryLite>().catch(() => []),
      listBehavioralQuestions<BehavioralQuestionLite>().catch(() => []),
      slug
        ? (async () => {
            const all = await listAnecdotes().catch(() => [] as Anecdote[]);
            setAnecdotes(all);
            const byTitle = all.find((a) => slugify(a.title) === slug);
            if (byTitle) return byTitle;
            const byId = all.find((a) => a.id === slug);
            return byId ?? null;
          })()
        : listAnecdotes().then((all) => {
            setAnecdotes(all);
            return null;
          }).catch(() => null),
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
    const titleSlug = slugify(form.title);
    const duplicate = anecdotes.some(
      (a) => a.id !== existingId && slugify(a.title) === titleSlug
    );
    if (duplicate) {
      setError('An anecdote with this title already exists. Choose a different title.');
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
        await updateAnecdote(existingId, body);
      } else {
        await createAnecdote(body);
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
      await deleteAnecdote(existingId);
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
          chromeActions={
            isEdit && existingId ? (
              <SaveAsBulletButton
                anecdoteId={existingId}
                seedText={
                  form.result?.trim() ||
                  form.action?.trim() ||
                  form.description?.trim() ||
                  form.title.trim()
                }
              />
            ) : undefined
          }
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

// "Save as bullet" lifts a one-line achievement out of an anecdote
// into the global Bullet Library so it can be reused across resumes
// and variants. The seed text comes from the anecdote's "Result" (or
// the next best STAR field), and the user can edit before saving so
// the bullet reads as a finished resume line, not a raw STAR sentence.
function SaveAsBulletButton({
  anecdoteId,
  seedText,
}: {
  anecdoteId: string;
  seedText: string;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState(seedText);
  const [tagsRaw, setTagsRaw] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const onOpen = () => {
    setText(seedText);
    setTagsRaw('');
    setError(null);
    setOpen(true);
  };

  const onSave = async () => {
    if (!text.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await createBullet({
        text: text.trim(),
        tags: tagsRaw
          .split(',')
          .map((t) => t.trim().toLowerCase())
          .filter(Boolean),
        source_anecdote_id: anecdoteId,
      });
      setOpen(false);
      setSavedAt(Date.now());
      window.setTimeout(() => setSavedAt(null), 2400);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={onOpen}
        className="inline-flex items-center gap-1.5"
        style={{
          padding: '8px 12px',
          borderRadius: 'var(--radius)',
          border: 0,
          background: 'transparent',
          boxShadow: 'inset 0 0 0 1px var(--border-strong)',
          color: 'var(--text-2)',
          fontSize: 12.5,
          fontWeight: 500,
          cursor: 'pointer',
        }}
        title="Save a one-line bullet from this anecdote into the Bullet Library"
      >
        <Sparkles size={13} strokeWidth={1.7} />
        Save as bullet
        {savedAt !== null && (
          <span
            style={{
              marginLeft: 4,
              fontSize: 10,
              color: 'var(--forest)',
              letterSpacing: '0.04em',
            }}
          >
            saved
          </span>
        )}
      </button>
      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Save bullet"
          onClick={() => setOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.45)',
            zIndex: 60,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="card"
            style={{ width: '100%', maxWidth: 520, padding: 0, display: 'flex', flexDirection: 'column' }}
          >
            <div
              className="flex items-center justify-between"
              style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}
            >
              <div>
                <div className="eyebrow" style={{ fontSize: 9.5, marginBottom: 2 }}>
                  Bullet library
                </div>
                <div style={{ fontSize: 13, fontWeight: 500 }}>Save as bullet</div>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close"
                style={{
                  background: 'transparent',
                  border: 0,
                  padding: 4,
                  borderRadius: 6,
                  boxShadow: 'inset 0 0 0 1px var(--border)',
                  color: 'var(--text-2)',
                  cursor: 'pointer',
                  display: 'inline-flex',
                }}
              >
                <X size={14} strokeWidth={1.8} />
              </button>
            </div>
            <div
              style={{
                padding: 16,
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
              }}
            >
              <label className="flex flex-col gap-1.5">
                <span className="eyebrow" style={{ fontSize: 9.5 }}>
                  Bullet
                </span>
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  rows={3}
                  placeholder="A one-line achievement, e.g. Reduced p99 latency 40% by sharding the order pipeline."
                  style={{
                    padding: '8px 10px',
                    background: 'var(--bg-elev)',
                    boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                    borderRadius: 'var(--radius)',
                    border: 0,
                    fontSize: 12.5,
                    color: 'var(--text)',
                    outline: 'none',
                    fontFamily: 'inherit',
                    lineHeight: 1.45,
                    resize: 'vertical',
                  }}
                />
                <span style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
                  Seeded from this anecdote's Result. Trim it to a resume-ready line and add
                  metrics where you can.
                </span>
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="eyebrow" style={{ fontSize: 9.5 }}>
                  Tags (optional)
                </span>
                <input
                  value={tagsRaw}
                  onChange={(e) => setTagsRaw(e.target.value)}
                  placeholder="e.g. leadership, infrastructure, scaling"
                  style={{
                    padding: '8px 10px',
                    background: 'var(--bg-elev)',
                    boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                    borderRadius: 'var(--radius)',
                    border: 0,
                    fontSize: 12.5,
                    color: 'var(--text)',
                    outline: 'none',
                  }}
                />
              </label>
              {error && (
                <div role="alert" style={{ fontSize: 11.5, color: 'var(--plum)' }}>
                  {error}
                </div>
              )}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={onSave}
                  disabled={saving || !text.trim()}
                  style={{
                    padding: '8px 14px',
                    borderRadius: 'var(--radius)',
                    border: 0,
                    background: 'var(--accent)',
                    color: 'var(--bg-elev)',
                    fontSize: 12.5,
                    fontWeight: 500,
                    cursor: saving || !text.trim() ? 'not-allowed' : 'pointer',
                    opacity: saving || !text.trim() ? 0.6 : 1,
                  }}
                >
                  {saving ? 'Saving…' : 'Save bullet'}
                </button>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  style={{
                    padding: '8px 12px',
                    background: 'transparent',
                    border: 0,
                    color: 'var(--text-3)',
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
