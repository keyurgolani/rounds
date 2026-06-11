// frontend/src/experience/ImportReview.tsx
import { useState, useCallback, useMemo, useRef, useEffect, useLayoutEffect, useReducer } from 'react';
import { Check } from 'lucide-react';
import { ConnectorOverlay, type Connector } from '../pages/behavioral/ConnectorOverlay';
import { LinkableCard } from '../pages/behavioral/LinkableCard';
import {
  createJob, createProject, createAnecdote, createBullet,
  deleteJob, deleteProject, deleteAnecdote, deleteBullet,
  type ExperienceJob, type ExperienceProject, type ExperienceAnecdote, type ExperienceBullet,
  type EntityKind,
} from './experienceApi';
import { batchCreateConnections, getJunctionTable } from './connectionApi';
import type { ExtractionResult, ExtractedJob, ExtractedProject, ExtractedAnecdote, ExtractedBullet } from './importApi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ExtractedItem {
  localId: string; // unique within this review
  kind: EntityKind;
  included: boolean;
  data: ExtractedJob | ExtractedProject | ExtractedAnecdote | ExtractedBullet;
}

interface LocalConnection {
  parentLocalId: string;
  childLocalId: string;
}

interface Props {
  result: ExtractionResult;
  onComplete: () => void;
  onCancel: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const TYPE_COLORS: Record<EntityKind, { bg: string; text: string }> = {
  job: { bg: 'var(--ink-soft)', text: 'var(--ink)' },
  project: { bg: 'var(--ochre-soft)', text: 'var(--ochre)' },
  anecdote: { bg: 'var(--accent-soft)', text: 'var(--accent)' },
  bullet: { bg: 'var(--forest-soft)', text: 'var(--forest)' },
};

const TYPE_LABELS: Record<EntityKind, string> = { job: 'Jobs', project: 'Projects', anecdote: 'Anecdotes', bullet: 'Bullets' };

function localId(kind: EntityKind, index: number) { return `${kind}-${index}`; }

function primaryLabel(item: ExtractedItem): string {
  switch (item.kind) {
    case 'job': return (item.data as ExtractedJob).company || 'Untitled Job';
    case 'project': return (item.data as ExtractedProject).title || 'Untitled Project';
    case 'anecdote': return (item.data as ExtractedAnecdote).title || 'Untitled Anecdote';
    case 'bullet': return (item.data as ExtractedBullet).title || 'Untitled Bullet';
    default: return 'Untitled';
  }
}

function secondaryLabel(item: ExtractedItem): string | undefined {
  switch (item.kind) {
    case 'job': return (item.data as ExtractedJob).role || undefined;
    case 'project': return (item.data as ExtractedProject).company || undefined;
    case 'anecdote': return (item.data as ExtractedAnecdote).situation?.slice(0, 80) || undefined;
    case 'bullet': return (item.data as ExtractedBullet).impact || undefined;
  }
}

// ---------------------------------------------------------------------------
// Field sanitizers — AI extraction may leave required fields empty or malformed.
// Required fields must be non-empty or PocketBase rejects the create.
// ---------------------------------------------------------------------------

const EMPLOYMENT_TYPES = ['full-time', 'contract', 'part-time', 'internship', 'freelance'];
const BULLET_CATEGORIES = ['leadership', 'technical', 'process', 'business', 'other'];

function today(): string {
  return new Date().toISOString().split('T')[0];
}

/** A required date: keep a valid YYYY-MM-DD, otherwise fall back to today. */
function reqDate(value?: string): string {
  const v = value?.trim();
  return v && /^\d{4}-\d{2}-\d{2}/.test(v) ? v : today();
}

/** An optional date (e.g. end_date): valid YYYY-MM-DD or null ("Present"). */
function optDate(value?: string): string | null {
  const v = value?.trim();
  return v && /^\d{4}-\d{2}-\d{2}/.test(v) ? v : null;
}

/** A required text field: trimmed value, or the provided fallback if empty. */
function reqText(value: string | undefined, fallback: string): string {
  return value?.trim() || fallback;
}

/** A select value: keep only if it's one of the allowed options, else empty. */
function oneOf(value: string | undefined, allowed: string[]): string {
  const v = value?.trim().toLowerCase();
  return v && allowed.includes(v) ? v : '';
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ImportReview({ result, onComplete, onCancel }: Props) {
  // Build items
  const [items, setItems] = useState<ExtractedItem[]>(() => {
    const all: ExtractedItem[] = [];
    result.jobs.forEach((d, i) => all.push({ localId: localId('job', i), kind: 'job', included: true, data: d }));
    result.projects.forEach((d, i) => all.push({ localId: localId('project', i), kind: 'project', included: true, data: d }));
    result.anecdotes.forEach((d, i) => all.push({ localId: localId('anecdote', i), kind: 'anecdote', included: true, data: d }));
    result.bullets.forEach((d, i) => all.push({ localId: localId('bullet', i), kind: 'bullet', included: true, data: d }));
    return all;
  });

  const [connections, setConnections] = useState<LocalConnection[]>(() =>
    result.connections
      .map((c) => ({
        parentLocalId: localId(c.parent_type, c.parent_index),
        childLocalId: localId(c.child_type, c.child_index),
      }))
      .filter((c) => items.some((i) => i.localId === c.parentLocalId) && items.some((i) => i.localId === c.childLocalId)),
  );

  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [tickValue, tick] = useReducer((n: number) => n + 1, 0);

  // --- Drag state ---
  const [drag, setDrag] = useState<{ fromId: string; fromX: number; fromY: number; x: number; y: number } | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);

  // Group items by kind
  const grouped = useMemo(() => {
    const groups: Record<EntityKind, ExtractedItem[]> = { job: [], project: [], anecdote: [], bullet: [] };
    for (const item of items) groups[item.kind].push(item);
    return groups;
  }, [items]);

  // Connection set for quick lookup
  const connSet = useMemo(() => {
    const s = new Set<string>();
    for (const c of connections) s.add(`${c.parentLocalId}::${c.childLocalId}`);
    return s;
  }, [connections]);

  function isConnected(a: string, b: string) {
    return connSet.has(`${a}::${b}`) || connSet.has(`${b}::${a}`);
  }

  function isActive(id: string) {
    if (!hoveredId) return false;
    if (hoveredId === id) return true;
    return isConnected(hoveredId, id);
  }

  function isDimmed(id: string) {
    if (!hoveredId) return false;
    return !isActive(id);
  }

  // Toggle included
  function toggleIncluded(localId: string) {
    setItems((prev) => prev.map((i) => i.localId === localId ? { ...i, included: !i.included } : i));
  }

  // Remove connection
  function removeConnection(parentId: string, childId: string) {
    setConnections((prev) => prev.filter((c) => !(c.parentLocalId === parentId && c.childLocalId === childId)));
  }

  // Add connection (from drag)
  function addConnection(fromId: string, toId: string) {
    const fromItem = items.find((i) => i.localId === fromId);
    const toItem = items.find((i) => i.localId === toId);
    if (!fromItem || !toItem) return;

    // Determine parent/child based on hierarchy
    const hierarchy: Record<EntityKind, number> = { job: 0, project: 1, anecdote: 2, bullet: 3 };
    const [parent, child] = hierarchy[fromItem.kind] < hierarchy[toItem.kind]
      ? [fromItem, toItem]
      : [toItem, fromItem];

    if (!getJunctionTable(parent.kind, child.kind)) return; // invalid pair

    const key = `${parent.localId}::${child.localId}`;
    if (connSet.has(key)) {
      // Toggle off
      removeConnection(parent.localId, child.localId);
    } else {
      setConnections((prev) => [...prev, { parentLocalId: parent.localId, childLocalId: child.localId }]);
    }
  }

  // --- Drag handling ---
  const beginDrag = useCallback((id: string, e: React.PointerEvent<HTMLSpanElement>) => {
    e.preventDefault();
    e.stopPropagation();
    const el = cardRefs.current[id];
    if (!el || !containerRef.current) return;
    const rect = el.getBoundingClientRect();
    const cRect = containerRef.current.getBoundingClientRect();
    setDrag({
      fromId: id,
      fromX: rect.right - cRect.left,
      fromY: rect.top - cRect.top + rect.height / 2,
      x: e.clientX - cRect.left,
      y: e.clientY - cRect.top,
    });
  }, []);

  useEffect(() => {
    if (!drag) return;
    const handleMove = (e: PointerEvent) => {
      const cRect = containerRef.current?.getBoundingClientRect();
      if (!cRect) return;
      setDrag((d) => d ? { ...d, x: e.clientX - cRect.left, y: e.clientY - cRect.top } : d);
      // Hit test
      for (const [id, el] of Object.entries(cardRefs.current)) {
        if (!el) continue;
        const r = el.getBoundingClientRect();
        if (e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom) {
          setDropTarget(id);
          return;
        }
      }
      setDropTarget(null);
    };
    const handleUp = () => {
      if (drag && dropTarget && dropTarget !== drag.fromId) {
        addConnection(drag.fromId, dropTarget);
      }
      setDrag(null);
      setDropTarget(null);
    };
    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
    return () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };
  }, [drag, dropTarget]);

  // --- Connectors ---
  const connectors: Connector[] = useMemo(() => {
    if (!containerRef.current) return [];
    const cRect = containerRef.current.getBoundingClientRect();
    const out: Connector[] = [];
    for (const c of connections) {
      const pEl = cardRefs.current[c.parentLocalId];
      const cEl = cardRefs.current[c.childLocalId];
      if (!pEl || !cEl) continue;
      const pr = pEl.getBoundingClientRect();
      const cr = cEl.getBoundingClientRect();
      out.push({
        key: `${c.parentLocalId}-${c.childLocalId}`,
        from: { x: pr.right - cRect.left, y: pr.top - cRect.top + pr.height / 2 },
        to: { x: cr.left - cRect.left, y: cr.top - cRect.top + cr.height / 2 },
        active: hoveredId === c.parentLocalId || hoveredId === c.childLocalId,
      });
    }
    return out;
  }, [connections, hoveredId, items, tickValue]);

  // Re-measure connector endpoints once card refs are in the DOM. Runs before
  // paint so the lines appear on first render instead of waiting for a hover.
  useLayoutEffect(() => { tick(); }, [items, connections]);

  // --- Counts ---
  const includedItems = useMemo(() => items.filter((i) => i.included), [items]);
  const includedConnections = useMemo(() =>
    connections.filter((c) =>
      includedItems.some((i) => i.localId === c.parentLocalId) &&
      includedItems.some((i) => i.localId === c.childLocalId),
    ),
    [connections, includedItems],
  );

  // Roll back created entities (best-effort). Deleting an entity cascade-deletes
  // its junction rows, so connections created during this run go with them.
  async function rollback(created: Array<{ kind: EntityKind; id: string }>) {
    for (const c of [...created].reverse()) {
      try {
        if (c.kind === 'job') await deleteJob(c.id);
        else if (c.kind === 'project') await deleteProject(c.id);
        else if (c.kind === 'anecdote') await deleteAnecdote(c.id);
        else await deleteBullet(c.id);
      } catch {
        // ignore — best effort
      }
    }
  }

  // --- Import execution (atomic: any failure rolls back everything) ---
  async function executeImport() {
    setImporting(true);
    setImportError(null);
    const idMap: Record<string, string> = {}; // localId → PocketBase ID
    const created: Array<{ kind: EntityKind; id: string }> = [];

    try {
      for (const item of includedItems) {
        let pbId: string;
        switch (item.kind) {
          case 'job': {
            const d = item.data as ExtractedJob;
            pbId = (await createJob({
              company: reqText(d.company, 'Untitled'),
              role: reqText(d.role, '—'),
              location: d.location,
              employment_type: oneOf(d.employment_type, EMPLOYMENT_TYPES),
              start_date: reqDate(d.start_date),
              end_date: optDate(d.end_date),
              description: d.description,
              tags: d.tags,
            })).id;
            break;
          }
          case 'project': {
            const d = item.data as ExtractedProject;
            pbId = (await createProject({
              title: reqText(d.title, 'Untitled Project'),
              company: d.company,
              role: d.role,
              team_size: d.team_size,
              tech_stack: d.tech_stack,
              start_date: reqDate(d.start_date),
              end_date: optDate(d.end_date),
              description: d.description,
              tags: d.tags,
            })).id;
            break;
          }
          case 'anecdote': {
            const d = item.data as ExtractedAnecdote;
            pbId = (await createAnecdote({
              title: reqText(d.title, 'Untitled Anecdote'),
              situation: d.situation,
              task: d.task,
              action: d.action,
              result: d.result,
              impact: d.impact,
              company: d.company,
              project: d.project,
              date: reqDate(d.date),
              tags: d.tags,
            })).id;
            break;
          }
          case 'bullet': {
            const d = item.data as ExtractedBullet;
            pbId = (await createBullet({
              title: reqText(d.title, 'Untitled Bullet'),
              impact: d.impact,
              category: oneOf(d.category, BULLET_CATEGORIES),
              date: reqDate(d.date),
              tags: d.tags,
            })).id;
            break;
          }
          default:
            throw new Error(`Unknown entity kind: ${item.kind}`);
        }
        created.push({ kind: item.kind, id: pbId });
        idMap[item.localId] = pbId;
      }

      // Create connections
      const connectionPairs = includedConnections
        .map((c) => {
          const parentItem = items.find((i) => i.localId === c.parentLocalId);
          const childItem = items.find((i) => i.localId === c.childLocalId);
          if (!parentItem || !childItem) return null;
          return {
            parentKind: parentItem.kind,
            parentId: idMap[c.parentLocalId],
            childKind: childItem.kind,
            childId: idMap[c.childLocalId],
          };
        })
        .filter(Boolean) as Array<{ parentKind: EntityKind; parentId: string; childKind: EntityKind; childId: string }>;

      await batchCreateConnections(connectionPairs);
      onComplete();
    } catch (e) {
      // Atomic: undo everything so no partial state remains.
      await rollback(created);
      setImportError(
        `Import failed and was rolled back — nothing was saved. ${e instanceof Error ? e.message : String(e)}`,
      );
    } finally {
      setImporting(false);
    }
  }

  const kinds: EntityKind[] = ['job', 'project', 'anecdote', 'bullet'];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Import Review"
      onClick={onCancel}
      style={{
        position: 'fixed', inset: 0, zIndex: 50,
        background: 'rgba(0, 0, 0, 0.45)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 24,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(1040px, 100%)',
          maxHeight: 'calc(100vh - 48px)',
          background: 'var(--bg)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-elev)',
          display: 'flex', flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
      {/* Header */}
      <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: 'var(--text)' }}>Import Review</h2>
        <p style={{ fontSize: 13, color: 'var(--text-3)', margin: '4px 0 0' }}>
          Review extracted items. Check/uncheck to include. Drag between cards to connect.
        </p>
      </div>

      {/* Content */}
      <div ref={containerRef} className="flex-1 min-h-0 overflow-auto" style={{ padding: 24, position: 'relative' }}>
        <ConnectorOverlay connectors={connectors} drag={drag ?? undefined} hasDropTarget={!!dropTarget} />

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 24, position: 'relative', zIndex: 2 }}>
          {kinds.map((kind) => {
            const groupItems = grouped[kind];
            if (groupItems.length === 0) return null;
            const colors = TYPE_COLORS[kind];

            return (
              <div key={kind}>
                <div className="mono" style={{ fontSize: 11, letterSpacing: '0.08em', color: colors.text, marginBottom: 12 }}>
                  {TYPE_LABELS[kind].toUpperCase()} ({groupItems.filter((i) => i.included).length}/{groupItems.length})
                </div>
                <div className="flex flex-col gap-3">
                  {groupItems.map((item) => (
                    <LinkableCard
                      key={item.localId}
                      innerRef={(el) => { cardRefs.current[item.localId] = el; }}
                      onMouseEnter={() => setHoveredId(item.localId)}
                      onMouseLeave={() => setHoveredId(null)}
                      onBeginDrag={(e) => beginDrag(item.localId, e)}
                      active={isActive(item.localId)}
                      dimmed={isDimmed(item.localId)}
                      isDropTarget={dropTarget === item.localId}
                      isDragSource={drag?.fromId === item.localId}
                      side="right"
                      compact={kind === 'bullet' || kind === 'anecdote'}
                    >
                      <div className="flex items-start gap-2">
                        <input
                          type="checkbox"
                          checked={item.included}
                          onChange={() => toggleIncluded(item.localId)}
                          style={{ marginTop: 2, accentColor: colors.text }}
                        />
                        <div className="flex-1 min-w-0">
                          <div style={{ fontSize: 14, fontWeight: 500, color: item.included ? 'var(--text)' : 'var(--text-4)', lineHeight: 1.3 }}>
                            {primaryLabel(item)}
                          </div>
                          {secondaryLabel(item) && (
                            <div className="line-clamp-1" style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>
                              {secondaryLabel(item)}
                            </div>
                          )}
                        </div>
                      </div>
                    </LinkableCard>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer */}
      <div style={{ padding: '12px 24px', borderTop: '1px solid var(--border)', flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
        {importError ? (
          <span style={{ fontSize: 12, color: 'var(--plum)', lineHeight: 1.4, minWidth: 0 }}>
            {importError}
          </span>
        ) : (
          <span className="mono" style={{ fontSize: 11, color: 'var(--text-4)' }}>
            {includedItems.length} items · {includedConnections.length} connections
          </span>
        )}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            style={{ padding: '8px 16px', border: 0, borderRadius: 'var(--radius)', background: 'var(--bg-sunken)', color: 'var(--text-2)', fontSize: 13, cursor: 'pointer' }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={executeImport}
            disabled={importing || includedItems.length === 0}
            data-ai-processing-glow={importing ? 'true' : undefined}
            className="flex items-center gap-1.5"
            style={{
              padding: '8px 20px', border: 0, borderRadius: 'var(--radius)',
              background: 'var(--accent)', color: 'var(--accent-fg, var(--paper))',
              fontSize: 13, fontWeight: 500, cursor: importing ? 'wait' : 'pointer',
              opacity: !importing && includedItems.length === 0 ? 0.6 : 1,
            }}
          >
            <Check size={14} />
            {importing ? 'Importing…' : `Import ${includedItems.length} items`}
          </button>
        </div>
      </div>
      </div>
    </div>
  );
}
