import { useState, useCallback } from 'react';
import SubmissionModal from '../components/shell/SubmissionModal';
import InlineEditField from '../applications/InlineEditField';
import type { ExperienceBullet } from './experienceApi';
import { updateBullet, deleteBullet } from './experienceApi';

const CATEGORY_OPTIONS = [
  { value: '', label: '—' },
  { value: 'leadership', label: 'Leadership' },
  { value: 'technical', label: 'Technical' },
  { value: 'process', label: 'Process' },
  { value: 'business', label: 'Business' },
  { value: 'other', label: 'Other' },
];

interface Props {
  item: ExperienceBullet | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export default function BulletModal({ item, open, onClose, onSaved }: Props) {
  const [saving, setSaving] = useState(false);

  const commit = useCallback(
    async (patch: Partial<ExperienceBullet>) => {
      if (!item) return;
      setSaving(true);
      try {
        await updateBullet(item.id, patch);
        onSaved();
      } finally {
        setSaving(false);
      }
    },
    [item, onSaved],
  );

  const handleDelete = useCallback(async () => {
    if (!item || !window.confirm('Delete this bullet?')) return;
    await deleteBullet(item.id);
    onSaved();
    onClose();
  }, [item, onClose, onSaved]);

  if (!item) return null;

  return (
    <SubmissionModal
      open={open}
      onClose={onClose}
      title={item.title || 'Bullet'}
      subtitle="Achievement · Click any field to edit"
    >
      <div className="flex flex-col gap-4" style={{ opacity: saving ? 0.6 : 1 }}>
        <InlineEditField kind="text" label="Title" value={item.title} onCommit={(next) => commit({ title: next })} />
        <InlineEditField kind="date-only" label="Date" value={item.date} onCommit={(next) => commit({ date: next })} />
        <InlineEditField kind="select" label="Category" value={item.category} options={CATEGORY_OPTIONS} onCommit={(next) => commit({ category: next })} />
        <InlineEditField kind="text" label="Impact" value={item.impact} onCommit={(next) => commit({ impact: next })} />

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
