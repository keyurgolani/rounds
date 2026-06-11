// frontend/src/experience/ArrangeInspector.tsx
//
// Side panel for the pinned card on the Arrange board. Surfaces the existing
// ConnectionSection (the same parents/children chip + search UI used inside the
// entity modals) plus Edit / Delete actions, so the board needs no new link UI.
import { X, Pencil, Trash2 } from 'lucide-react';
import type { TimelineEntity } from './experienceApi';
import ConnectionSection, { type ConnectionProps } from './ConnectionSection';
import { TYPE_COLORS, TYPE_LABELS } from './ConnectionCanvas';

interface Props {
  entity: TimelineEntity;
  title: string;
  subtitle?: string;
  /** Shared connection bundle (same one the modals receive). */
  connection: ConnectionProps;
  /** Navigate the pin to another entity (used by chip clicks). */
  onNavigate: (id: string) => void;
  onEdit: () => void;
  onDelete: () => void;
  onClose: () => void;
}

export default function ArrangeInspector({
  entity, title, subtitle, connection, onNavigate, onEdit, onDelete, onClose,
}: Props) {
  const colors = TYPE_COLORS[entity.kind];
  return (
    <div className="card" style={{ padding: 16, position: 'sticky', top: 0 }}>
      <div className="flex items-start justify-between" style={{ gap: 8, marginBottom: 10 }}>
        <span
          className="mono"
          style={{
            fontSize: 9.5, fontWeight: 700, letterSpacing: '0.08em',
            color: colors.text, background: colors.bg, padding: '2px 7px', borderRadius: 5,
          }}
        >
          {TYPE_LABELS[entity.kind].toUpperCase().replace(/S$/, '')}
        </span>
        <button
          type="button"
          aria-label="Close inspector"
          onClick={onClose}
          style={{ background: 0, border: 0, cursor: 'pointer', color: 'var(--text-4)', padding: 2, display: 'inline-flex' }}
        >
          <X size={15} />
        </button>
      </div>

      <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3 }}>{title}</div>
      {subtitle && (
        <div className="line-clamp-2" style={{ fontSize: 12.5, color: 'var(--text-3)', marginTop: 2 }}>
          {subtitle}
        </div>
      )}

      <div style={{ marginTop: 14 }}>
        <ConnectionSection
          entityId={entity.id}
          entityKind={entity.kind}
          {...connection}
          onNavigate={(_kind, id) => onNavigate(id)}
        />
      </div>

      <div className="flex items-center gap-2" style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
        <button
          type="button"
          onClick={onEdit}
          className="flex items-center gap-1.5"
          style={{ fontSize: 12, padding: '6px 12px', border: 0, borderRadius: 'var(--radius)', background: 'var(--ink)', color: 'var(--paper)', cursor: 'pointer' }}
        >
          <Pencil size={13} /> Edit details
        </button>
        <button
          type="button"
          onClick={onDelete}
          aria-label="Delete"
          className="flex items-center gap-1.5"
          style={{ fontSize: 12, padding: '6px 12px', borderRadius: 'var(--radius)', background: 'transparent', color: 'var(--plum)', border: '1px solid var(--border)', cursor: 'pointer' }}
        >
          <Trash2 size={13} /> Delete
        </button>
      </div>
    </div>
  );
}
