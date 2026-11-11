// The share pages' fixed toolbar label and their Read-only badge
// (ROUNDS-00B-L03). Neither ever shows anything from a response.

import { Eye } from 'lucide-react';

export const SHARE_TOOLBAR_LABEL = 'Shared resume, read-only';

export function ReadOnlyBadge() {
  return (
    <span
      className="inline-flex items-center gap-1.5"
      title="This view is shared via a public link"
      style={{
        padding: '6px 10px',
        borderRadius: 8,
        background: 'var(--bg-sunken)',
        color: 'var(--text-3)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
        fontSize: 11,
        fontWeight: 500,
      }}
    >
      <Eye size={12} strokeWidth={1.8} aria-hidden="true" />
      Read-only
    </span>
  );
}
