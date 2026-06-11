// frontend/src/experience/ArrangeBoard.tsx
//
// Live wiring board over existing entities. Hover a card to see its links; click
// to pin it and edit in the inspector. Drag a card's handle onto another to link,
// or use the inspector's search. Every change writes to the database immediately.
import { useState, useMemo, useCallback, useEffect } from 'react';
import {
  deleteJob, deleteProject, deleteAnecdote, deleteBullet,
  type TimelineEntity, type EntityKind,
} from './experienceApi';
import { createConnection, deleteConnection, type Connection } from './connectionApi';
import type { ConnectionProps } from './ConnectionSection';
import ConnectionCanvas, { type CanvasItem, type CanvasConnection } from './ConnectionCanvas';
import ArrangeInspector from './ArrangeInspector';
import { linkMetaByEntity, isUnfiled } from './arrangeMetadata';

interface Props {
  entities: TimelineEntity[];
  connections: Connection[];
  /** Shared connection bundle (same one the entity modals receive). */
  connection: ConnectionProps;
  /** Reload timeline data after any mutation. */
  onChanged: () => void;
  /** Open an entity's edit modal. */
  onOpen: (entity: TimelineEntity) => void;
}

function cardTitle(e: TimelineEntity): string {
  switch (e.kind) {
    case 'job': return e.company || 'Untitled Job';
    case 'project': return e.title || 'Untitled Project';
    case 'anecdote': return e.title || 'Untitled Anecdote';
    case 'bullet': return e.title || 'Untitled Bullet';
  }
}

function cardSubtitle(e: TimelineEntity): string | undefined {
  switch (e.kind) {
    case 'job': return e.role || undefined;
    case 'project': return [e.company, e.role].filter(Boolean).join(' · ') || undefined;
    case 'anecdote': return e.result || e.situation || undefined;
    case 'bullet': return e.impact || undefined;
  }
}

const DELETE_FN: Record<EntityKind, (id: string) => Promise<void>> = {
  job: deleteJob, project: deleteProject, anecdote: deleteAnecdote, bullet: deleteBullet,
};

export default function ArrangeBoard({ entities, connections, connection, onChanged, onOpen }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  const entityById = useMemo(() => {
    const m: Record<string, TimelineEntity> = {};
    for (const e of entities) m[e.id] = e;
    return m;
  }, [entities]);

  const meta = useMemo(() => linkMetaByEntity(connections), [connections]);

  const canvasItems: CanvasItem[] = useMemo(
    () => entities.map((e) => ({
      localId: e.id,
      kind: e.kind,
      flag: isUnfiled(e.kind, meta[e.id]) ? ('unfiled' as const) : undefined,
    })),
    [entities, meta],
  );

  const canvasConnections: CanvasConnection[] = useMemo(
    () => connections.map((c) => ({ parentLocalId: c.parentId, childLocalId: c.childId })),
    [connections],
  );

  const byPair = useMemo(() => {
    const m: Record<string, Connection> = {};
    for (const c of connections) m[`${c.parentId}::${c.childId}`] = c;
    return m;
  }, [connections]);

  // Drop the pin if its entity disappears (e.g. after a delete + reload).
  useEffect(() => {
    if (selectedId && !entityById[selectedId]) setSelectedId(null);
  }, [entityById, selectedId]);

  // Escape clears the pin.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setSelectedId(null); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Run a mutation, then reload. Serialized via `busy` to avoid racing writes.
  const run = useCallback(async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await fn();
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [busy, onChanged]);

  const removeLink = useCallback((parentId: string, childId: string) => {
    const conn = byPair[`${parentId}::${childId}`];
    if (!conn) return;
    run(() => deleteConnection(conn));
  }, [byPair, run]);

  const onToggleLink = useCallback((parentLocalId: string, childLocalId: string, alreadyLinked: boolean) => {
    if (alreadyLinked) {
      removeLink(parentLocalId, childLocalId);
      return;
    }
    const parent = entityById[parentLocalId];
    const child = entityById[childLocalId];
    if (!parent || !child) return;
    run(() => createConnection(parent.kind, parentLocalId, child.kind, childLocalId).then(() => {}));
  }, [entityById, removeLink, run]);

  const handleDelete = useCallback((entity: TimelineEntity) => {
    const ok = window.confirm(`Delete "${cardTitle(entity)}"? This also removes its connections. This cannot be undone.`);
    if (!ok) return;
    setSelectedId(null);
    run(() => DELETE_FN[entity.kind](entity.id));
  }, [run]);

  const renderCardContent = useCallback((ci: CanvasItem) => {
    const entity = entityById[ci.localId];
    if (!entity) return null;
    const subtitle = cardSubtitle(entity);
    const m = meta[entity.id];
    const total = m?.total ?? 0;
    const unfiled = ci.flag === 'unfiled';
    return (
      <div className="flex flex-col" style={{ minWidth: 0 }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text)', lineHeight: 1.3 }}>
          {cardTitle(entity)}
        </div>
        {subtitle && (
          <div className="line-clamp-1" style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>
            {subtitle}
          </div>
        )}
        <div style={{ marginTop: 6 }}>
          {total > 0 ? (
            <span
              className="mono"
              style={{ fontSize: 10, background: 'var(--bg-sunken)', color: 'var(--text-3)', padding: '2px 7px', borderRadius: 999, boxShadow: 'inset 0 0 0 1px var(--border)' }}
            >
              {total} linked
            </span>
          ) : unfiled ? (
            <span
              className="mono"
              style={{ fontSize: 10, color: 'var(--text-3)', padding: '1px 7px', borderRadius: 999, border: '1px dashed var(--border-strong)', letterSpacing: '0.06em' }}
            >
              UNFILED
            </span>
          ) : null}
        </div>
      </div>
    );
  }, [entityById, meta]);

  const selectedEntity = selectedId ? entityById[selectedId] : null;

  return (
    <div style={{ position: 'relative', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="flex items-center justify-between" style={{ marginBottom: 16, flexShrink: 0, gap: 16 }}>
        <p style={{ fontSize: 13, color: 'var(--text-3)', margin: 0 }}>
          Hover a card to see its links; click to pin it and edit in the panel. Drag a
          card's handle onto another to connect, or use the inspector's search. Changes
          save instantly.
        </p>
        <label
          className="mono flex items-center gap-2"
          style={{ fontSize: 11, color: 'var(--text-3)', flexShrink: 0, cursor: 'pointer', whiteSpace: 'nowrap' }}
        >
          <input
            type="checkbox"
            checked={showAll}
            onChange={(e) => setShowAll(e.target.checked)}
            style={{ accentColor: 'var(--accent)', cursor: 'pointer' }}
          />
          Show all connections
        </label>
      </div>

      {error && (
        <div className="card" style={{ padding: '8px 14px', marginBottom: 14, color: 'var(--plum)', fontSize: 12, flexShrink: 0 }}>
          {error}
        </div>
      )}

      <div className="flex" style={{ flex: 1, minHeight: 0, gap: 20 }}>
        <div style={{ flex: 1, minWidth: 0, opacity: busy ? 0.7 : 1, transition: 'opacity 140ms' }}>
          <ConnectionCanvas
            items={canvasItems}
            connections={canvasConnections}
            renderCardContent={renderCardContent}
            onToggleLink={onToggleLink}
            onDisconnect={removeLink}
            interaction={showAll ? 'always' : 'focus'}
            selectedId={selectedId}
            onSelectItem={(id) => setSelectedId((prev) => (prev === id ? null : id))}
            columnScroll
          />
        </div>
        {selectedEntity && (
          <div style={{ width: 336, flexShrink: 0, minHeight: 0, overflowY: 'auto', padding: '4px 8px' }}>
            <ArrangeInspector
              entity={selectedEntity}
              title={cardTitle(selectedEntity)}
              subtitle={cardSubtitle(selectedEntity)}
              connection={connection}
              onNavigate={(id) => setSelectedId(id)}
              onEdit={() => onOpen(selectedEntity)}
              onDelete={() => handleDelete(selectedEntity)}
              onClose={() => setSelectedId(null)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
