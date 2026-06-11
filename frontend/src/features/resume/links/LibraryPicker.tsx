import { useState, useEffect, useCallback } from 'react';
import { X, ChevronRight, ChevronDown } from 'lucide-react';
import { loadLibrarySnapshot } from './library';
import type { LibraryData } from './library';
import type { ExperienceJob, ExperienceProject } from '../../../experience/experienceApi';

export interface PickResult {
  ref: string;
  bulletIds: string[];
  bulletTitles: string[];
}

interface Props {
  kind: 'job' | 'project';
  open: boolean;
  onClose: () => void;
  onPick: (sel: PickResult) => void;
}

export default function LibraryPicker({ kind, open, onClose, onPick }: Props) {
  const [snapshot, setSnapshot] = useState<LibraryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  // Record<itemId, Set<bulletId>> — which bullets are checked per item
  const [checked, setChecked] = useState<Record<string, Set<string>>>({});

  // Load snapshot when modal opens
  useEffect(() => {
    if (!open) return;
    setSnapshot(null);
    setExpandedId(null);
    setChecked({});
    setLoading(true);
    loadLibrarySnapshot()
      .then((snap) => {
        setSnapshot(snap);
        // Initialize all items' checked sets up front from the snapshot
        const initialChecked: Record<string, Set<string>> = {};
        const items =
          kind === 'job' ? Object.values(snap.jobs) : Object.values(snap.projects);
        for (const item of items) {
          const bulletIds = snap.connMap[item.id]?.bullet ?? [];
          initialChecked[item.id] = new Set(bulletIds);
        }
        setChecked(initialChecked);
      })
      .finally(() => setLoading(false));
  }, [open, kind]);

  // Escape key and body scroll lock
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  const toggleBullet = useCallback((itemId: string, bulletId: string) => {
    setChecked((prev) => {
      const next = { ...prev };
      const set = new Set(prev[itemId] ?? []);
      if (set.has(bulletId)) {
        set.delete(bulletId);
      } else {
        set.add(bulletId);
      }
      next[itemId] = set;
      return next;
    });
  }, []);

  const handlePick = useCallback(
    (itemId: string) => {
      if (!snapshot) return;
      const connectedBulletIds = snapshot.connMap[itemId]?.bullet ?? [];
      const checkedSet = checked[itemId] ?? new Set<string>();
      // Preserve connMap order, only include checked ones
      const bulletIds = connectedBulletIds.filter((id) => checkedSet.has(id));
      const bulletTitles = bulletIds.map((id) => snapshot.bullets[id]?.title ?? '');
      onPick({ ref: itemId, bulletIds, bulletTitles });
      onClose();
    },
    [snapshot, checked, onPick, onClose],
  );

  if (!open) return null;

  const itemLabel = (item: ExperienceJob | ExperienceProject): string => {
    if ('company' in item && 'role' in item && item.role) {
      return `${(item as ExperienceJob).role} · ${(item as ExperienceJob).company}`;
    }
    return (item as ExperienceProject).title;
  };

  const items = snapshot
    ? kind === 'job'
      ? Object.values(snapshot.jobs)
      : Object.values(snapshot.projects)
    : [];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Add from library"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        background: 'rgba(0, 0, 0, 0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(560px, 100%)',
          maxHeight: 'calc(100vh - 48px)',
          background: 'var(--bg)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-elev)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          className="flex items-start gap-3"
          style={{
            padding: '16px 20px 12px',
            borderBottom: '1px solid var(--border)',
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <h2
              style={{
                fontSize: 22,
                lineHeight: 1.15,
                margin: 0,
                color: 'var(--text)',
                fontWeight: 600,
              }}
            >
              Add from library
            </h2>
            <p
              style={{
                margin: '4px 0 0',
                fontSize: 12.5,
                color: 'var(--text-3)',
                lineHeight: 1.45,
              }}
            >
              Expand a {kind} to choose which bullets to include.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            title="Close (Esc)"
            style={{
              width: 28,
              height: 28,
              border: 0,
              borderRadius: 6,
              background: 'var(--bg-sunken)',
              color: 'var(--text-2)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              boxShadow: 'inset 0 0 0 1px var(--border)',
            }}
          >
            <X size={14} strokeWidth={2} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: 16, flex: 1, overflow: 'auto', minHeight: 0 }}>
          {loading && (
            <p style={{ color: 'var(--text-3)', fontSize: 13, textAlign: 'center', padding: 24 }}>
              Loading…
            </p>
          )}

          {!loading && items.length === 0 && (
            <p style={{ color: 'var(--text-3)', fontSize: 13, textAlign: 'center', padding: 24 }}>
              No {kind}s found in your library.
            </p>
          )}

          {!loading && items.map((item) => {
            const isExpanded = expandedId === item.id;
            const connectedBulletIds = snapshot?.connMap[item.id]?.bullet ?? [];
            const checkedSet = checked[item.id] ?? new Set<string>();

            return (
              <div
                key={item.id}
                style={{
                  marginBottom: 8,
                  borderRadius: 'var(--radius)',
                  boxShadow: 'inset 0 0 0 1px var(--border)',
                  background: 'var(--bg-elev)',
                  overflow: 'hidden',
                }}
              >
                {/* Item header / expander */}
                <button
                  type="button"
                  onClick={() => setExpandedId(isExpanded ? null : item.id)}
                  className="flex items-center gap-2 w-full"
                  style={{
                    padding: '10px 14px',
                    border: 0,
                    background: 'transparent',
                    cursor: 'pointer',
                    color: 'var(--text)',
                    fontSize: 14,
                    fontWeight: 500,
                    textAlign: 'left',
                    width: '100%',
                  }}
                >
                  {isExpanded ? (
                    <ChevronDown size={14} strokeWidth={2} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
                  ) : (
                    <ChevronRight size={14} strokeWidth={2} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
                  )}
                  <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {itemLabel(item)}
                  </span>
                  {connectedBulletIds.length > 0 && (
                    <span
                      style={{
                        fontSize: 11,
                        color: 'var(--text-3)',
                        flexShrink: 0,
                        marginLeft: 4,
                      }}
                    >
                      {connectedBulletIds.length} bullet{connectedBulletIds.length !== 1 ? 's' : ''}
                    </span>
                  )}
                </button>

                {/* Expanded bullets */}
                {isExpanded && (
                  <div
                    style={{
                      borderTop: '1px solid var(--border)',
                      padding: '8px 14px 12px',
                    }}
                  >
                    {connectedBulletIds.length === 0 && (
                      <p style={{ fontSize: 12.5, color: 'var(--text-3)', margin: 0 }}>
                        No bullets connected to this {kind}.
                      </p>
                    )}

                    {connectedBulletIds.map((bulletId) => {
                      const bullet = snapshot?.bullets[bulletId];
                      if (!bullet) return null;
                      const isChecked = checkedSet.has(bulletId);
                      return (
                        <label
                          key={bulletId}
                          className="flex items-start gap-2"
                          style={{
                            display: 'flex',
                            alignItems: 'flex-start',
                            gap: 8,
                            padding: '5px 0',
                            cursor: 'pointer',
                            fontSize: 13,
                            color: 'var(--text)',
                            lineHeight: 1.45,
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleBullet(item.id, bulletId)}
                            style={{ marginTop: 2, flexShrink: 0, accentColor: 'var(--accent)' }}
                          />
                          <span>{bullet.title}</span>
                        </label>
                      );
                    })}

                    {connectedBulletIds.length > 0 && (
                      <button
                        type="button"
                        onClick={() => handlePick(item.id)}
                        style={{
                          marginTop: 10,
                          padding: '8px 16px',
                          border: 0,
                          borderRadius: 'var(--radius)',
                          background: 'var(--accent)',
                          color: 'var(--accent-fg, var(--paper))',
                          fontSize: 13,
                          fontWeight: 500,
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                        }}
                      >
                        Add to resume
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
