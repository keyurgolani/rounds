// frontend/src/experience/ListTree.tsx
//
// The Experience "List" tab body. In the default ("all") view it renders every
// entity as a nested outline of cards: jobs and unfiled items are roots, each
// child indents below its parent joined by a left rail + elbow, and a child with
// multiple parents appears under each. Cards get denser with depth. Clicking a
// card opens its editor (connection edits stay in the modals / Arrange board).
import { useCallback, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { TimelineEntity, EntityKind } from './experienceApi';
import type { ConnectionMap, ReverseConnectionMap } from './connectionApi';
import {
  TYPE_COLORS,
  TYPE_LABELS,
  depthCfg,
  entityDate,
  childIdsOf,
  subtreeMaxDate,
  formatDate,
  rowTitle,
  rowSubtitle,
} from './experienceTree';

const INDENT = 26;                       // children-block indent per level (px)
const RAIL_X = 7;                        // vertical rail offset within the gutter
const ELBOW_W = INDENT - RAIL_X - 3;     // horizontal elbow length into the card
const BADGE_HALF_H = 8; // ~half the badge/label row height, to center the elbow on it
const elbowY = (depth: number) => depthCfg(depth).pt + BADGE_HALF_H;

const KIND_RANK: Record<EntityKind, number> = { project: 0, anecdote: 1, bullet: 2, job: 3 };

interface Props {
  entities: TimelineEntity[];
  connMap: ConnectionMap;
  reverseMap: ReverseConnectionMap;
  entityById: Record<string, TimelineEntity>;
  /** 'all' (nested) or an EntityKind (flat list of that kind). */
  filter: string;
  onOpen: (entity: TimelineEntity) => void;
}

/** Ancestry-filtered, kind-ordered, date-desc children from a precomputed direct list. */
function orderChildren(
  direct: { kind: EntityKind; id: string }[],
  ancestry: Set<string>,
  entityById: Record<string, TimelineEntity>,
): { kind: EntityKind; id: string }[] {
  return direct
    .filter((c) => !ancestry.has(c.id) && entityById[c.id])
    .sort((a, b) => {
      const kr = KIND_RANK[a.kind] - KIND_RANK[b.kind];
      if (kr !== 0) return kr;
      return +new Date(entityDate(entityById[b.id])) - +new Date(entityDate(entityById[a.id]));
    });
}

interface CardProps {
  entity: TimelineEntity;
  depth: number;
  expandable: boolean;
  expanded: boolean;
  childCount: number;
  onToggle?: () => void;
  onOpen: (entity: TimelineEntity) => void;
}

/** One entity card. Denser as depth grows; subtitle hidden at depth >= 2. */
function EntityCard({ entity, depth, expandable, expanded, childCount, onToggle, onOpen }: CardProps) {
  const colors = TYPE_COLORS[entity.kind];
  const cfg = depthCfg(depth);
  const subtitle = depth < 2 ? rowSubtitle(entity) : undefined;

  return (
    <button
      type="button"
      onClick={() => onOpen(entity)}
      className="text-left w-full"
      style={{
        padding: cfg.padding,
        borderLeft: `${depth === 0 ? 3 : 2}px solid ${colors.text}`,
        borderRadius: 'var(--radius)',
        background: 'var(--bg-elev)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
        cursor: 'pointer',
        transition: 'box-shadow 120ms, transform 120ms',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = 'inset 0 0 0 1px var(--border), 0 4px 12px rgba(0,0,0,0.1)';
        e.currentTarget.style.transform = 'translateY(-1px)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = 'inset 0 0 0 1px var(--border)';
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      <div className="flex items-center gap-2 flex-wrap" style={{ marginBottom: subtitle ? 3 : 0 }}>
        <span className="pill mono" style={{ fontSize: 8.5, letterSpacing: '0.08em', background: colors.bg, color: colors.text, padding: '2px 7px' }}>
          {TYPE_LABELS[entity.kind].toUpperCase()}
        </span>
        <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>{formatDate(entity)}</span>
        {childCount > 0 && (
          <span className="mono pill" style={{ fontSize: 10, background: 'var(--bg-sunken)', color: 'var(--text-3)', padding: '2px 8px', boxShadow: 'inset 0 0 0 1px var(--border)' }}>
            {childCount} linked
          </span>
        )}
        {expandable && (
          <span
            role="button"
            tabIndex={0}
            onClick={(e) => { e.stopPropagation(); onToggle?.(); }}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); onToggle?.(); } }}
            className="flex items-center ml-auto"
            style={{ cursor: 'pointer', color: 'var(--text-3)' }}
            title={expanded ? 'Collapse' : 'Expand'}
            aria-label={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          </span>
        )}
      </div>
      <div style={{ fontSize: cfg.title, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3 }}>
        {rowTitle(entity)}
      </div>
      {subtitle && (
        <div className="line-clamp-1" style={{ fontSize: 12.5, color: 'var(--text-2)', marginTop: 2 }}>
          {subtitle}
        </div>
      )}
    </button>
  );
}

interface NodeProps {
  entity: TimelineEntity;
  depth: number;
  pathKey: string;
  ancestry: Set<string>;
  connMap: ConnectionMap;
  entityById: Record<string, TimelineEntity>;
  collapsedSet: Set<string>;
  toggle: (key: string) => void;
  onOpen: (entity: TimelineEntity) => void;
}

/** Recursive node: a card plus, when expanded, its children indented below and
 *  joined by a left rail + per-child elbow. Cycle-guarded via `ancestry`. */
function ListTreeNode({ entity, depth, pathKey, ancestry, connMap, entityById, collapsedSet, toggle, onOpen }: NodeProps) {
  const directChildren = childIdsOf(connMap, entity.id); // entity's total direct links (path-independent)
  const children = orderChildren(directChildren, ancestry, entityById);
  const expandable = children.length > 0;
  const expanded = !collapsedSet.has(pathKey);
  const childAncestry = new Set(ancestry).add(entity.id);
  const railX = depth * INDENT + RAIL_X;

  return (
    <div style={{ position: 'relative' }}>
      <div style={{ paddingLeft: depth * INDENT }}>
        <EntityCard
          entity={entity}
          depth={depth}
          expandable={expandable}
          expanded={expanded}
          childCount={directChildren.length} // path-independent total; intentionally not children.length
          onToggle={() => toggle(pathKey)}
          onOpen={onOpen}
        />
      </div>
      {expandable && expanded && (
        <div style={{ marginTop: 6 }}>
          {children.map((c, i) => {
            const isLast = i === children.length - 1;
            const ey = elbowY(depth + 1);
            const childPathKey = `${pathKey}>${c.id}`;
            return (
              <div key={childPathKey} style={{ position: 'relative', paddingBottom: isLast ? 0 : 6 }}>
                {/* vertical rail: spans the whole sibling row, except the last stops at its elbow */}
                <div style={{ position: 'absolute', left: railX, top: 0, height: isLast ? ey : '100%', width: 1.5, background: 'var(--border-strong)' }} />
                {/* elbow into the child card */}
                <div style={{ position: 'absolute', left: railX, top: ey, width: ELBOW_W, height: 1.5, background: 'var(--border-strong)' }} />
                <ListTreeNode
                  entity={entityById[c.id]}
                  depth={depth + 1}
                  pathKey={childPathKey}
                  ancestry={childAncestry}
                  connMap={connMap}
                  entityById={entityById}
                  collapsedSet={collapsedSet}
                  toggle={toggle}
                  onOpen={onOpen}
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

interface FlatRowProps {
  entity: TimelineEntity;
  connMap: ConnectionMap;
  onOpen: (entity: TimelineEntity) => void;
}

/** A single flat row, used when the List is filtered to one kind. */
function FlatRow({ entity, connMap, onOpen }: FlatRowProps) {
  const linked = childIdsOf(connMap, entity.id).length;
  const subtitle = rowSubtitle(entity);
  return (
    <button
      type="button"
      onClick={() => onOpen(entity)}
      className="text-left w-full flex items-center gap-4"
      style={{
        padding: '14px 18px',
        borderRadius: 'var(--radius)',
        background: 'var(--bg-elev)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
        cursor: 'pointer',
        transition: 'box-shadow 120ms',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.boxShadow = 'inset 0 0 0 1px var(--border), 0 2px 8px rgba(0,0,0,0.08)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.boxShadow = 'inset 0 0 0 1px var(--border)'; }}
    >
      <div className="flex-1 min-w-0">
        <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text)', marginBottom: 2 }}>
          {rowTitle(entity)}
        </div>
        {subtitle && (
          <p className="line-clamp-1" style={{ fontSize: 12.5, color: 'var(--text-3)', margin: 0 }}>
            {subtitle}
          </p>
        )}
      </div>
      {linked > 0 && (
        <span className="mono pill flex-shrink-0" style={{ fontSize: 10, background: 'var(--bg-sunken)', color: 'var(--text-3)', padding: '2px 8px', boxShadow: 'inset 0 0 0 1px var(--border)' }}>
          {linked} linked
        </span>
      )}
      <span className="mono flex-shrink-0" style={{ fontSize: 11, color: 'var(--text-4)' }}>
        {formatDate(entity)}
      </span>
    </button>
  );
}

export default function ListTree({ entities, connMap, reverseMap, entityById, filter, onOpen }: Props) {
  const [collapsedSet, setCollapsedSet] = useState<Set<string>>(new Set());
  const toggle = useCallback((key: string) => {
    setCollapsedSet((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }, []);

  const nested = filter === 'all';

  const roots = useMemo(
    () =>
      nested
        ? entities
            .filter((e) => !reverseMap[e.id])
            .sort((a, b) => subtreeMaxDate(b.id, connMap, entityById) - subtreeMaxDate(a.id, connMap, entityById))
        : [],
    [nested, entities, reverseMap, connMap, entityById],
  );

  const flat = useMemo(
    () => (nested ? [] : entities.filter((e) => e.kind === filter)),
    [nested, entities, filter],
  );

  if (!nested) {
    return (
      <div className="flex flex-col gap-2">
        {flat.map((e) => (
          <FlatRow key={e.id} entity={e} connMap={connMap} onOpen={onOpen} />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {roots.map((e) => (
        <ListTreeNode
          key={e.id}
          entity={e}
          depth={0}
          pathKey={e.id}
          ancestry={new Set()}
          connMap={connMap}
          entityById={entityById}
          collapsedSet={collapsedSet}
          toggle={toggle}
          onOpen={onOpen}
        />
      ))}
    </div>
  );
}
