// frontend/src/experience/ConnectionSection.tsx
import { useState, useCallback } from 'react';
import { Link2, X } from 'lucide-react';
import type { EntityKind } from './experienceApi';
import {
  type Connection, type ConnectionMap,
  deleteConnection, createConnection,
  validChildKinds, validParentKinds, getJunctionTable,
} from './connectionApi';

export interface LinkedEntity {
  id: string;
  kind: EntityKind;
  label: string;
}

/**
 * Bundle of connection data shared by every entity modal. Built once on the
 * Experience page and passed down so each modal can render its connections.
 */
export interface ConnectionProps {
  connections: Connection[];
  connMap: ConnectionMap;
  reverseMap: ConnectionMap;
  allEntities: LinkedEntity[];
  onConnectionChanged: () => void;
  onNavigate: (kind: EntityKind, id: string) => void;
}

interface Props extends ConnectionProps {
  entityId: string;
  entityKind: EntityKind;
}

const KIND_COLORS: Record<EntityKind, string> = {
  job: 'var(--ink)',
  project: 'var(--ochre)',
  anecdote: 'var(--accent)',
  bullet: 'var(--forest)',
};

export default function ConnectionSection({
  entityId, entityKind, connections, connMap, reverseMap, allEntities, onConnectionChanged, onNavigate,
}: Props) {
  const [linking, setLinking] = useState(false);
  const [search, setSearch] = useState('');

  // Find connected entities (children + parents).
  const connectedIds = new Set<string>();
  const children = connMap[entityId] ?? { job: [], project: [], anecdote: [], bullet: [] };
  const parents = reverseMap[entityId] ?? { job: [], project: [], anecdote: [], bullet: [] };
  for (const ids of Object.values(children)) ids.forEach((id) => connectedIds.add(id));
  for (const ids of Object.values(parents)) ids.forEach((id) => connectedIds.add(id));

  const connectedEntities = allEntities.filter((e) => connectedIds.has(e.id));

  // Find valid link targets.
  const validKinds = [...validChildKinds(entityKind), ...validParentKinds(entityKind)];
  const availableEntities = allEntities.filter(
    (e) => validKinds.includes(e.kind) && !connectedIds.has(e.id) && e.id !== entityId,
  );
  const filtered = search
    ? availableEntities.filter((e) => e.label.toLowerCase().includes(search.toLowerCase()))
    : availableEntities.slice(0, 10);

  const handleRemove = useCallback(async (targetId: string) => {
    const conn = connections.find(
      (c) => (c.parentId === entityId && c.childId === targetId) || (c.childId === entityId && c.parentId === targetId),
    );
    if (conn) {
      await deleteConnection(conn);
      onConnectionChanged();
    }
  }, [connections, entityId, onConnectionChanged]);

  const handleAdd = useCallback(async (target: LinkedEntity) => {
    // Determine parent/child by hierarchy depth.
    const hierarchy: Record<EntityKind, number> = { job: 0, project: 1, anecdote: 2, bullet: 3 };
    const [parentKind, parentId, childKind, childId] = hierarchy[entityKind] < hierarchy[target.kind]
      ? [entityKind, entityId, target.kind, target.id] as const
      : [target.kind, target.id, entityKind, entityId] as const;

    if (getJunctionTable(parentKind, childKind)) {
      await createConnection(parentKind, parentId, childKind, childId);
      onConnectionChanged();
    }
    setLinking(false);
    setSearch('');
  }, [entityKind, entityId, onConnectionChanged]);

  return (
    <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
      <div className="flex items-center justify-between mb-2">
        <span className="eyebrow" style={{ color: 'var(--text-3)' }}>Connections</span>
        {!linking && (
          <button
            type="button"
            onClick={() => setLinking(true)}
            className="flex items-center gap-1"
            style={{ background: 0, border: 0, cursor: 'pointer', color: 'var(--text-3)', fontSize: 11 }}
          >
            <Link2 size={12} /> Link
          </button>
        )}
      </div>

      {connectedEntities.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {connectedEntities.map((e) => (
            <span
              key={e.id}
              className="pill flex items-center gap-1"
              style={{ fontSize: 11, padding: '3px 8px', background: KIND_COLORS[e.kind] + '18', color: KIND_COLORS[e.kind] }}
            >
              <span style={{ cursor: 'pointer' }} onClick={() => onNavigate(e.kind, e.id)}>{e.label}</span>
              <button type="button" onClick={() => handleRemove(e.id)} style={{ background: 0, border: 0, cursor: 'pointer', color: 'var(--text-4)', padding: 0, lineHeight: 1, display: 'inline-flex' }}>
                <X size={10} />
              </button>
            </span>
          ))}
        </div>
      ) : (
        !linking && <p style={{ fontSize: 12, color: 'var(--text-4)', margin: 0 }}>No connections yet.</p>
      )}

      {linking && (
        <div style={{ marginTop: 8 }}>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search entities…"
            autoFocus
            style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '6px 10px', fontSize: 12, background: 'var(--bg)', color: 'var(--text)', width: '100%', outline: 'none' }}
          />
          {filtered.length > 0 ? (
            <div className="flex flex-wrap gap-1" style={{ marginTop: 6 }}>
              {filtered.map((e) => (
                <button
                  key={e.id}
                  type="button"
                  onClick={() => handleAdd(e)}
                  className="pill"
                  style={{ fontSize: 11, padding: '3px 8px', background: KIND_COLORS[e.kind] + '10', color: KIND_COLORS[e.kind], border: 0, borderRadius: 999, cursor: 'pointer' }}
                >
                  + {e.label}
                </button>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: 11, color: 'var(--text-4)', margin: '6px 0 0' }}>No matching entities to link.</p>
          )}
          <button type="button" onClick={() => { setLinking(false); setSearch(''); }} style={{ background: 0, border: 0, cursor: 'pointer', color: 'var(--text-4)', fontSize: 11, marginTop: 4 }}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
