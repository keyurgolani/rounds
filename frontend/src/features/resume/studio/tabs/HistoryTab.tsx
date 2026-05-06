// Version history list with restore. Powered by `resume_versions` rows
// stamped by useResume. Manual labels can be added later — for now any
// row with `is_auto = false` is treated as user-created.

import { useEffect, useState } from 'react';
import { listVersions } from '../../api';
import type { Resume, ResumeData, ResumeVersion } from '../../types';

type Props = {
  resume: Resume | null;
  onRestore: (data: ResumeData) => void;
};

export default function HistoryTab({ resume, onRestore }: Props) {
  const [versions, setVersions] = useState<ResumeVersion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!resume) return;
    setLoading(true);
    listVersions({ resumeId: resume.id })
      .then(setVersions)
      .finally(() => setLoading(false));
  }, [resume, resume?.updated_at]);

  if (!resume) return null;

  return (
    <div className="flex flex-col gap-2">
      <div className="eyebrow" style={{ fontSize: 9.5 }}>
        Version history
      </div>
      <p style={{ margin: 0, fontSize: 11.5, color: 'var(--text-4)', lineHeight: 1.5 }}>
        Auto-saves stamp a snapshot at most once per minute. Restoring overwrites the current
        draft (and starts a fresh autosave thread).
      </p>
      {loading ? (
        <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Loading…</div>
      ) : versions.length === 0 ? (
        <div className="card" style={{ padding: 12, fontSize: 12, color: 'var(--text-3)' }}>
          No snapshots yet. Edit anything and the first auto-version will appear here.
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          {versions.map((v) => (
            <div
              key={v.id}
              className="card flex items-center justify-between"
              style={{ padding: '8px 10px' }}
            >
              <div>
                <div className="mono" style={{ fontSize: 10.5, color: 'var(--text-3)' }}>
                  {new Date(v.created_at).toLocaleString()}
                </div>
                <div style={{ fontSize: 12 }}>
                  {v.label ? v.label : v.is_auto ? 'Auto-save' : 'Manual snapshot'}
                </div>
              </div>
              <button
                type="button"
                onClick={() => onRestore(v.data)}
                style={{
                  padding: '5px 10px',
                  background: 'transparent',
                  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                  borderRadius: 'var(--radius)',
                  border: 0,
                  color: 'var(--text-2)',
                  fontSize: 11,
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                Restore
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
