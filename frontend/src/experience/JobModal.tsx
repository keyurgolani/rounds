import { useState, useCallback } from 'react';
import SubmissionModal from '../components/shell/SubmissionModal';
import InlineEditField from '../applications/InlineEditField';
import type { ExperienceJob } from './experienceApi';
import { updateJob, deleteJob } from './experienceApi';

const EMPLOYMENT_OPTIONS = [
  { value: '', label: '—' },
  { value: 'full-time', label: 'Full-time' },
  { value: 'contract', label: 'Contract' },
  { value: 'part-time', label: 'Part-time' },
  { value: 'internship', label: 'Internship' },
  { value: 'freelance', label: 'Freelance' },
];

interface Props {
  item: ExperienceJob | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export default function JobModal({ item, open, onClose, onSaved }: Props) {
  const [saving, setSaving] = useState(false);

  const commit = useCallback(
    async (patch: Partial<ExperienceJob>) => {
      if (!item) return;
      setSaving(true);
      try {
        await updateJob(item.id, patch);
        onSaved();
      } finally {
        setSaving(false);
      }
    },
    [item, onSaved],
  );

  const handleDelete = useCallback(async () => {
    if (!item || !window.confirm('Delete this job?')) return;
    await deleteJob(item.id);
    onSaved();
    onClose();
  }, [item, onClose, onSaved]);

  if (!item) return null;

  return (
    <SubmissionModal
      open={open}
      onClose={onClose}
      title={item.company || 'Job'}
      subtitle={`${item.role} · Click any field to edit`}
    >
      <div className="flex flex-col gap-4" style={{ opacity: saving ? 0.6 : 1 }}>
        <InlineEditField kind="text" label="Company" value={item.company} onCommit={(next) => commit({ company: next })} />
        <InlineEditField kind="text" label="Role" value={item.role} onCommit={(next) => commit({ role: next })} />
        <div className="flex gap-4">
          <div className="flex-1">
            <InlineEditField kind="date-only" label="Start Date" value={item.start_date} onCommit={(next) => commit({ start_date: next })} />
          </div>
          <div className="flex-1">
            <InlineEditField kind="date-only" label="End Date" value={item.end_date ?? ''} onCommit={(next) => commit({ end_date: next || null })} />
          </div>
        </div>
        <InlineEditField kind="text" label="Location" value={item.location} onCommit={(next) => commit({ location: next })} />
        <InlineEditField kind="select" label="Employment Type" value={item.employment_type} options={EMPLOYMENT_OPTIONS} onCommit={(next) => commit({ employment_type: next })} />
        <InlineEditField kind="multiline" label="Description" value={item.description} onCommit={(next) => commit({ description: next })} rows={4} />

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
