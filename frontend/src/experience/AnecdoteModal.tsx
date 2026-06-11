import { useState, useCallback } from 'react';
import { X } from 'lucide-react';
import SubmissionModal from '../components/shell/SubmissionModal';
import InlineEditField from '../applications/InlineEditField';
import type { ExperienceAnecdote } from './experienceApi';
import { updateAnecdote, deleteAnecdote } from './experienceApi';
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
        <InlineEditField kind="multiline" label="Situation" value={item.situation} onCommit={(next) => commit({ situation: next })} rows={2} />
        <InlineEditField kind="multiline" label="Task" value={item.task} onCommit={(next) => commit({ task: next })} rows={2} />
        <InlineEditField kind="multiline" label="Action" value={item.action} onCommit={(next) => commit({ action: next })} rows={2} />
        <InlineEditField kind="multiline" label="Result" value={item.result} onCommit={(next) => commit({ result: next })} rows={2} />
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

        {connection && (
          <ConnectionSection entityId={item.id} entityKind="anecdote" {...connection} />
        )}

        <div className="flex items-center justify-between pt-3" style={{ borderTop: '1px solid var(--border)' }}>
          <button
            type="button"
            onClick={handleDelete}
            className="mono"
            style={{ fontSize: 11, color: 'var(--plum)', background: 'transparent', border: 0, cursor: 'pointer' }}
          >
            Delete
          </button>
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