import { useState, useCallback, useEffect } from 'react';
import { X, Sparkles } from 'lucide-react';
import SubmissionModal from '../components/shell/SubmissionModal';
import InlineEditField from '../applications/InlineEditField';
import type { ExperienceAnecdote } from './experienceApi';
import { updateAnecdote, deleteAnecdote, createBullet } from './experienceApi';
import { createConnection } from './connectionApi';
import { listBehavioralCategories, listBehavioralQuestions } from '../content/api';
import type { BehavioralCategoryLite, BehavioralQuestionLite } from '../pages/behavioral/types';
import ConnectionSection, { type ConnectionProps } from './ConnectionSection';

interface Props {
  item: ExperienceAnecdote | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  connection?: ConnectionProps;
}

export default function AnecdoteModal({ item, open, onClose, onSaved, connection }: Props) {
  const [saving, setSaving] = useState(false);
  const [mode, setMode] = useState<'description' | 'star' | 'both'>('both');
  const [categories, setCategories] = useState<BehavioralCategoryLite[]>([]);
  const [questions, setQuestions] = useState<BehavioralQuestionLite[]>([]);

  useEffect(() => {
    if (!open) return;
    listBehavioralCategories<BehavioralCategoryLite>().then(setCategories).catch(() => {});
    listBehavioralQuestions<BehavioralQuestionLite>().then(setQuestions).catch(() => {});
  }, [open]);

  const commit = useCallback(
    async (patch: Partial<ExperienceAnecdote>) => {
      if (!item) return;
      setSaving(true);
      try {
        await updateAnecdote(item.id, patch);
        onSaved();
      } finally {
        setSaving(false);
      }
    },
    [item, onSaved],
  );

  const handleDelete = useCallback(async () => {
    if (!item || !window.confirm('Delete this anecdote?')) return;
    await deleteAnecdote(item.id);
    onSaved();
    onClose();
  }, [item, onClose, onSaved]);

  if (!item) return null;

  return (
    <SubmissionModal
      open={open}
      onClose={onClose}
      title={item.title || 'Anecdote'}
      subtitle={`${item.company || ''} ${item.project ? '· ' + item.project : ''} · Click any field to edit`}
    >
      <div className="flex flex-col gap-4" style={{ opacity: saving ? 0.6 : 1 }}>
        <InlineEditField kind="text" label="Title" value={item.title} onCommit={(next) => commit({ title: next })} />
        <InlineEditField kind="date-only" label="Date" value={item.date} onCommit={(next) => commit({ date: next })} />
        <InlineEditField kind="text" label="Company" value={item.company} onCommit={(next) => commit({ company: next })} />
        <InlineEditField kind="text" label="Project" value={item.project} onCommit={(next) => commit({ project: next })} />

        {/* Description / STAR / Both mode toggle */}
        <div className="flex items-center gap-1" style={{ background: 'var(--bg-sunken)', borderRadius: 'var(--radius)', padding: 3, width: 'fit-content' }}>
          {(['description', 'star', 'both'] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              style={{
                padding: '3px 10px',
                borderRadius: 'calc(var(--radius) - 2px)',
                border: 0,
                background: mode === m ? 'var(--bg-elev)' : 'transparent',
                color: mode === m ? 'var(--text)' : 'var(--text-3)',
                fontSize: 11,
                fontWeight: mode === m ? 600 : 400,
                cursor: 'pointer',
                boxShadow: mode === m ? '0 1px 3px rgba(0,0,0,0.12)' : 'none',
                transition: 'all 0.1s',
              }}
            >
              {m === 'star' ? 'STAR' : m === 'description' ? 'Description' : 'Both'}
            </button>
          ))}
        </div>

        {/* Description field */}
        {mode !== 'star' && (
          <InlineEditField kind="multiline" label="Description" value={item.description} onCommit={(next) => commit({ description: next })} rows={4} />
        )}

        {/* STAR fields */}
        {mode !== 'description' && (
          <>
            <InlineEditField kind="multiline" label="Situation" value={item.situation} onCommit={(next) => commit({ situation: next })} rows={2} />
            <InlineEditField kind="multiline" label="Task" value={item.task} onCommit={(next) => commit({ task: next })} rows={2} />
            <InlineEditField kind="multiline" label="Action" value={item.action} onCommit={(next) => commit({ action: next })} rows={2} />
            <InlineEditField kind="multiline" label="Result" value={item.result} onCommit={(next) => commit({ result: next })} rows={2} />
          </>
        )}

        <InlineEditField kind="text" label="Impact" value={item.impact} onCommit={(next) => commit({ impact: next })} />

        {/* Tags */}
        <div className="flex flex-col" style={{ gap: 4 }}>
          <span className="eyebrow" style={{ color: 'var(--text-3)' }}>Tags</span>
          <div className="flex flex-wrap gap-1.5 items-center">
            {item.tags.map((tag) => (
              <span key={tag} className="pill flex items-center gap-1" style={{ fontSize: 11, background: 'var(--bg-sunken)', color: 'var(--text-2)', boxShadow: 'inset 0 0 0 1px var(--border)', padding: '2px 8px' }}>
                {tag}
                <button type="button" onClick={() => commit({ tags: item.tags.filter((t) => t !== tag) })} style={{ background: 0, border: 0, cursor: 'pointer', color: 'var(--text-4)', padding: 0, lineHeight: 1, display: 'inline-flex' }}>
                  <X size={10} />
                </button>
              </span>
            ))}
            <TagInput onAdd={(tag) => { if (!item.tags.includes(tag)) commit({ tags: [...item.tags, tag] }); }} />
          </div>
        </div>

        {/* Categories */}
        <div className="flex flex-col" style={{ gap: 4 }}>
          <span className="eyebrow" style={{ color: 'var(--text-3)' }}>Categories</span>
          <div className="flex flex-wrap gap-1.5">
            {categories.map((c) => {
              const on = item.category_ids.includes(c.id);
              return (
                <button key={c.id} type="button" className="pill transition-colors"
                  onClick={() => commit({ category_ids: on
                    ? item.category_ids.filter((x) => x !== c.id)
                    : [...item.category_ids, c.id] })}
                  style={{ background: on ? c.color : 'transparent',
                    color: on ? 'var(--paper, #fff)' : c.color,
                    boxShadow: on ? 'none' : 'inset 0 0 0 1px var(--border-strong)' }}>
                  {c.name}
                </button>
              );
            })}
          </div>
        </div>

        {/* Linked questions */}
        <div className="flex flex-col" style={{ gap: 4 }}>
          <span className="eyebrow" style={{ color: 'var(--text-3)' }}>Linked questions</span>
          <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto">
            {questions.map((q) => {
              const on = item.linked_question_ids.includes(q.id);
              return (
                <button key={q.id} type="button" className="pill transition-colors text-left"
                  onClick={() => commit({ linked_question_ids: on
                    ? item.linked_question_ids.filter((x) => x !== q.id)
                    : [...item.linked_question_ids, q.id] })}
                  style={{ background: on ? 'var(--ink, var(--text))' : 'var(--bg-sunken)',
                    color: on ? 'var(--paper, var(--bg-elev))' : 'var(--text-3)',
                    boxShadow: on ? 'none' : 'inset 0 0 0 1px var(--border-strong)' }}>
                  {q.title}
                </button>
              );
            })}
          </div>
        </div>

        {/* Notes */}
        <InlineEditField kind="multiline" label="Notes" value={item.notes}
          onCommit={(next) => commit({ notes: next })} rows={3} />

        {connection && (
          <ConnectionSection entityId={item.id} entityKind="anecdote" {...connection} />
        )}

        <div className="flex items-center justify-between pt-3" style={{ borderTop: '1px solid var(--border)' }}>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleDelete}
              className="mono"
              style={{ fontSize: 11, color: 'var(--plum)', background: 'transparent', border: 0, cursor: 'pointer' }}
            >
              Delete
            </button>
            <SaveAsBulletButton
              anecdoteId={item.id}
              seedText={item.result || item.action || item.description || item.title}
              onSaved={onSaved}
            />
          </div>
          <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>Press Esc to close</span>
        </div>
      </div>
    </SubmissionModal>
  );
}

function TagInput({ onAdd }: { onAdd: (tag: string) => void }) {
  const [draft, setDraft] = useState('');
  return (
    <input
      type="text"
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          const t = draft.trim();
          if (t) { onAdd(t); setDraft(''); }
        }
      }}
      placeholder="Add tag…"
      style={{ border: 0, background: 'transparent', color: 'var(--text)', fontSize: 12, outline: 'none', width: 80, padding: '2px 0' }}
    />
  );
}

function SaveAsBulletButton({
  anecdoteId,
  seedText,
  onSaved,
}: {
  anecdoteId: string;
  seedText: string;
  onSaved: () => void;
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
      const tags = tagsRaw
        .split(',')
        .map((t) => t.trim().toLowerCase())
        .filter(Boolean);
      const newBullet = await createBullet({ title: text.trim(), tags });
      await createConnection('anecdote', anecdoteId, 'bullet', newBullet.id);
      onSaved();
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
