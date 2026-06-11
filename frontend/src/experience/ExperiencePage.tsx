import { useState, useCallback, useEffect, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  List,
  Network,
  Clock,
  Plus,
  Upload,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import AppHeader from '../components/shell/AppHeader';
import {
  listTimelineEntities,
  createJob,
  createProject,
  createAnecdote,
  createBullet,
  type TimelineEntity,
  type EntityKind,
  type ExperienceJob,
  type ExperienceProject,
  type ExperienceAnecdote,
  type ExperienceBullet,
} from './experienceApi';
import {
  listAllConnections,
  buildConnectionMap,
  buildReverseMap,
  connectionRefs,
  type Connection,
  type ConnectionMap,
} from './connectionApi';
import type { ConnectionProps, LinkedEntity } from './ConnectionSection';
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
import EntitySelector from './EntitySelector';
import ImportModal from './ImportModal';
import JobModal from './JobModal';
import ProjectModal from './ProjectModal';
import AnecdoteModal from './AnecdoteModal';
import BulletModal from './BulletModal';
import ArrangeBoard from './ArrangeBoard';
import ListTree from './ListTree';

// ---------------------------------------------------------------------------
// Tab definitions
// ---------------------------------------------------------------------------

const TABS = [
  { key: 'timeline' as const, label: 'Timeline', icon: Clock },
  { key: 'list' as const, label: 'List', icon: List },
  { key: 'arrange' as const, label: 'Arrange', icon: Network },
] as const;

type TabKey = (typeof TABS)[number]['key'];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function groupByYear(
  items: TimelineEntity[],
  dateOf: (e: TimelineEntity) => number,
): Record<string, TimelineEntity[]> {
  const groups: Record<string, TimelineEntity[]> = {};
  for (const item of items) {
    const year = new Date(dateOf(item)).getFullYear().toString();
    if (!groups[year]) groups[year] = [];
    groups[year].push(item);
  }
  for (const year of Object.keys(groups)) {
    groups[year].sort((a, b) => dateOf(b) - dateOf(a));
  }
  return groups;
}

// ---------------------------------------------------------------------------
// Nested children (timeline)
// ---------------------------------------------------------------------------

// Per-depth card sizing. `pt` is the top padding; used to align connectors to
// the badge/title row.
const anchorY = (d: number) => depthCfg(d).pt + 8; // badge-row centre from card top
const GUTTER = 22;     // tree indent per level (outer side)
const CENTER_GAP = 20; // card inner edge -> central line (per-card connector + node)

interface TreeNodeProps {
  entity: TimelineEntity;
  depth: number;
  pathKey: string;
  isRoot: boolean;
  isLeft: boolean;
  enableChildren: boolean;
  connMap: ConnectionMap;
  entityById: Record<string, TimelineEntity>;
  collapsedSet: Set<string>;
  ancestry: Set<string>;
  toggle: (key: string) => void;
  onClick: (entity: TimelineEntity) => void;
}

/** Recursive node. Children render ABOVE the card (further along the timeline
 *  sits higher) and branch off the parent via an outer spine + elbow; every
 *  card also taps the central line with its own connector + node. */
function TreeNode({ entity, depth, pathKey, isRoot, isLeft, enableChildren, connMap, entityById, collapsedSet, ancestry, toggle, onClick }: TreeNodeProps) {
  const colors = TYPE_COLORS[entity.kind];
  const cfg = depthCfg(depth);
  const children = enableChildren
    ? childIdsOf(connMap, entity.id).filter((c) => !ancestry.has(c.id) && entityById[c.id])
    : [];
  const expandable = children.length > 0;
  const expanded = !collapsedSet.has(pathKey);
  const anchor = anchorY(depth);
  const dot = isRoot ? 10 : 7;
  const spineX = depth * GUTTER + 8;

  const title = rowTitle(entity);
  const subtitle = rowSubtitle(entity);
  const showDescription = isRoot && (entity.kind === 'job' || entity.kind === 'project') && !!entity.description;
  const showTags = isRoot && entity.tags.length > 0;
  const accentWidth = isRoot ? 3 : 2;
  const cardBorder = isLeft
    ? { borderRight: `${accentWidth}px solid ${colors.text}` }
    : { borderLeft: `${accentWidth}px solid ${colors.text}` };
  const outerPos = (x: number) => (isLeft ? { left: x } : { right: x });

  return (
    <div style={{ position: 'relative' }}>
      {/* Children render ABOVE the parent */}
      {expandable && expanded && (
        <div style={{ position: 'relative' }}>
          {children.map((c, i) => {
            const isTop = i === 0;
            const childAnchor = anchorY(depth + 1);
            return (
              <div key={c.id} style={{ position: 'relative', paddingBottom: 6 }}>
                {/* vertical spine: from the topmost child's elbow down to the parent card */}
                <div style={{ position: 'absolute', ...outerPos(spineX), top: isTop ? childAnchor : 0, bottom: 0, width: 1.5, background: 'var(--border-strong)' }} />
                {/* horizontal elbow into the child card */}
                <div style={{ position: 'absolute', ...outerPos(spineX), top: childAnchor, width: GUTTER - 8, height: 1.5, background: 'var(--border-strong)' }} />
                <TreeNode
                  entity={entityById[c.id]}
                  depth={depth + 1}
                  pathKey={`${pathKey}>${c.id}`}
                  isRoot={false}
                  isLeft={isLeft}
                  enableChildren={enableChildren}
                  connMap={connMap}
                  entityById={entityById}
                  collapsedSet={collapsedSet}
                  ancestry={new Set(ancestry).add(entity.id)}
                  toggle={toggle}
                  onClick={onClick}
                />
              </div>
            );
          })}
        </div>
      )}

      {/* The card, tapping the central line with its own connector + node */}
      <div style={{ position: 'relative', ...(isLeft ? { paddingLeft: depth * GUTTER } : { paddingRight: depth * GUTTER }) }}>
        <button
          type="button"
          onClick={() => onClick(entity)}
          className="text-left w-full"
          style={{
            padding: cfg.padding,
            ...cardBorder,
            borderRadius: 'var(--radius)',
            background: 'var(--bg-elev)',
            boxShadow: 'inset 0 0 0 1px var(--border)',
            cursor: 'pointer',
            transition: 'box-shadow 120ms, transform 120ms',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.boxShadow = 'inset 0 0 0 1px var(--border), 0 4px 12px rgba(0,0,0,0.1)'; e.currentTarget.style.transform = 'translateY(-1px)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.boxShadow = 'inset 0 0 0 1px var(--border)'; e.currentTarget.style.transform = 'translateY(0)'; }}
        >
          <div className="flex items-center gap-2 flex-wrap" style={{ marginBottom: 3 }}>
            <span className="pill mono" style={{ fontSize: 8.5, letterSpacing: '0.08em', background: colors.bg, color: colors.text, padding: '2px 7px' }}>
              {TYPE_LABELS[entity.kind].toUpperCase()}
            </span>
            <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>{formatDate(entity)}</span>
            {expandable && (
              <span
                role="button"
                tabIndex={0}
                onClick={(e) => { e.stopPropagation(); toggle(pathKey); }}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); toggle(pathKey); } }}
                className="flex items-center ml-auto"
                style={{ cursor: 'pointer', color: 'var(--text-3)' }}
                title={expanded ? 'Collapse' : 'Expand'}
              >
                {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
              </span>
            )}
          </div>
          <div style={{ fontSize: cfg.title, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3 }}>{title}</div>
          {subtitle && <div className="line-clamp-1" style={{ fontSize: 12.5, color: 'var(--text-2)', marginTop: 2 }}>{subtitle}</div>}
          {showDescription && (
            <p className="line-clamp-2" style={{ fontSize: 13, color: 'var(--text-3)', lineHeight: 1.5, margin: '6px 0 0' }}>
              {(entity as ExperienceJob | ExperienceProject).description}
            </p>
          )}
          {showTags && (
            <div className="flex flex-wrap gap-1" style={{ marginTop: 8 }}>
              {entity.tags.slice(0, 6).map((tag) => (
                <span key={tag} className="pill" style={{ fontSize: 10, background: 'transparent', color: 'var(--text-4)', boxShadow: 'inset 0 0 0 1px var(--border)', padding: '1px 7px' }}>{tag}</span>
              ))}
            </div>
          )}
        </button>
        {/* connector + node tapping the central line (inner side).
            The connector is offset by half its height so it runs through the
            vertical centre of the node rather than just below it. */}
        <div style={{ position: 'absolute', top: anchor - 0.75, ...(isLeft ? { right: -CENTER_GAP } : { left: -CENTER_GAP }), width: CENTER_GAP, height: 1.5, background: colors.text, opacity: 0.45 }} />
        <div style={{ position: 'absolute', top: anchor - dot / 2, ...(isLeft ? { right: -(CENTER_GAP + dot / 2) } : { left: -(CENTER_GAP + dot / 2) }), width: dot, height: dot, borderRadius: 999, background: colors.text, border: '2px solid var(--bg)' }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

const PATH_TO_TAB: Record<string, TabKey> = {
  '/experience': 'timeline',
  '/experience/list': 'list',
  '/experience/arrange': 'arrange',
};

const TAB_TO_PATH: Record<TabKey, string> = {
  timeline: '/experience',
  list: '/experience/list',
  arrange: '/experience/arrange',
};

export default function ExperiencePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const activeTab = PATH_TO_TAB[location.pathname] ?? 'timeline';
  const [timelineItems, setTimelineItems] = useState<TimelineEntity[] | null>(null);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [collapsedSet, setCollapsedSet] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<TimelineEntity | (ExperienceJob | ExperienceProject | ExperienceAnecdote | ExperienceBullet) | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [filter, setFilter] = useState<string>('all');
  const [selectorOpen, setSelectorOpen] = useState(false);

  // Load timeline data
  const loadTimeline = useCallback(() => {
    setError(null);
    Promise.all([listTimelineEntities(), listAllConnections()])
      .then(([entities, conns]) => {
        setTimelineItems(entities);
        setConnections(conns);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const toggleCollapsed = useCallback((key: string) => {
    setCollapsedSet((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  useEffect(() => {
    // Timeline entities + connections back every tab: the timeline tree, the
    // flat List view, the Arrange board, the entity lookup, and modal navigation.
    loadTimeline();
  }, [loadTimeline]);

  // Sync selected after refresh
  useEffect(() => {
    if (!selected || !timelineItems) return;
    const updated = timelineItems.find((i) => i.id === selected.id);
    if (updated) setSelected(updated);
  }, [timelineItems, selected]);

  // Connection maps
  const connMap = useMemo(() => buildConnectionMap(connections), [connections]);
  const reverseMap = useMemo(() => buildReverseMap(connections), [connections]);
  const entityById = useMemo(() => {
    const map: Record<string, TimelineEntity> = {};
    for (const item of timelineItems ?? []) map[item.id] = item;
    return map;
  }, [timelineItems]);

  // True when the entity is a child of at least one connection (so it renders nested).
  const hasParent = useCallback((id: string) => Boolean(reverseMap[id]), [reverseMap]);

  // Filtered & grouped timeline.
  // In "all" view, connected children are hidden from the top level — they appear
  // nested under each parent. A type filter shows every item of that kind, flat.
  const filtered = useMemo(() => {
    if (!timelineItems) return null;
    if (filter === 'all') return timelineItems.filter((i) => !hasParent(i.id));
    return timelineItems.filter((i) => i.kind === filter);
  }, [timelineItems, filter, hasParent]);

  const grouped = useMemo(() => {
    if (!filtered) return null;
    // In "all" view a subtree's timeline position is its newest item (children
    // render above the parent); a type filter uses each item's own date.
    const dateOf = filter === 'all'
      ? (e: TimelineEntity) => subtreeMaxDate(e.id, connMap, entityById)
      : (e: TimelineEntity) => +new Date(entityDate(e));
    return groupByYear(filtered, dateOf);
  }, [filtered, filter, connMap, entityById]);

  const years = useMemo(() => {
    if (!grouped) return [];
    return Object.keys(grouped).sort((a, b) => +b - +a);
  }, [grouped]);

  // Data source for the List tab. In "all" mode this is every entity and ListTree
  // renders the nesting; a type filter narrows it to a flat subset of that kind.
  // Also drives the "… ITEMS" count in the filter bar.
  const listView = useMemo(() => {
    if (!timelineItems) return null;
    return filter === 'all' ? timelineItems : timelineItems.filter((i) => i.kind === filter);
  }, [timelineItems, filter]);

  // Handlers
  function handleCardClick(item: TimelineEntity | (ExperienceJob | ExperienceProject | ExperienceAnecdote | ExperienceBullet)) {
    setSelected(item);
    setModalOpen(true);
  }

  async function handleAdd(kind: EntityKind) {
    setSelectorOpen(false);
    const today = new Date().toISOString().split('T')[0];
    let newItem: TimelineEntity | (ExperienceJob | ExperienceProject | ExperienceAnecdote | ExperienceBullet);

    switch (kind) {
      case 'job':
        newItem = { kind: 'job', ...(await createJob({ company: 'New Company', role: 'Role', start_date: today })) };
        break;
      case 'project':
        newItem = { kind: 'project', ...(await createProject({ title: 'New Project', start_date: today })) };
        break;
      case 'anecdote':
        newItem = { kind: 'anecdote', ...(await createAnecdote({ title: 'New Anecdote', date: today })) };
        break;
      case 'bullet':
        newItem = { kind: 'bullet', ...(await createBullet({ title: 'New Bullet', date: today })) };
        break;
      default:
        throw new Error(`Unknown entity kind: ${kind}`);
    }

    setTimelineItems((prev) => (prev ? [newItem as TimelineEntity, ...prev] : [newItem as TimelineEntity]));
    setSelected(newItem);
    setModalOpen(true);
  }

  // Add always opens the entity-type picker (Timeline and List both).
  function handleAddForTab() {
    setSelectorOpen(true);
  }

  function reload() {
    loadTimeline();
  }

  // The selected entity's own kind (set on every TimelineEntity, including those
  // reached via connection navigation) drives which edit modal renders.
  const currentEntityKind: EntityKind | undefined =
    selected && 'kind' in selected ? (selected as TimelineEntity).kind : undefined;

  // All entities as link targets, plus a connection bundle shared by every modal.
  const allEntities = useMemo<LinkedEntity[]>(
    () =>
      (timelineItems ?? []).map((e) => ({
        id: e.id,
        kind: e.kind,
        label: e.kind === 'job' ? e.company : e.title,
      })),
    [timelineItems],
  );

  const handleNavigate = useCallback(
    (_kind: EntityKind, id: string) => {
      const entity = entityById[id];
      if (entity) {
        setSelected(entity);
        setModalOpen(true);
      }
    },
    [entityById],
  );

  const connectionBundle: ConnectionProps = {
    connections,
    connMap,
    reverseMap,
    allEntities,
    onConnectionChanged: reload,
    onNavigate: handleNavigate,
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="h-full flex flex-col min-h-0">
      <AppHeader
        eyebrow="Track · Experience"
        title="Experience"
        description="Your career journey: jobs, projects, stories, and achievements."
        chromeActions={
          <div style={{ position: 'relative', display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={() => setImportOpen(true)}
              className="inline-flex items-center gap-1.5"
              style={{
                padding: '6px 14px',
                border: 0,
                borderRadius: 'var(--radius)',
                background: 'transparent',
                color: 'var(--text-2)',
                fontSize: 12.5,
                fontWeight: 500,
                cursor: 'pointer',
                boxShadow: 'inset 0 0 0 1px var(--border-strong)',
              }}
            >
              <Upload size={14} strokeWidth={2} />
              Import
            </button>
            <button
              type="button"
              onClick={handleAddForTab}
              className="inline-flex items-center gap-1.5"
              style={{
                padding: '6px 14px',
                border: 0,
                borderRadius: 'var(--radius)',
                background: 'var(--accent)',
                color: 'var(--accent-fg, var(--paper))',
                fontSize: 12.5,
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              <Plus size={14} strokeWidth={2} />
              Add
            </button>
            {selectorOpen && (
              <EntitySelector onSelect={handleAdd} onClose={() => setSelectorOpen(false)} />
            )}
          </div>
        }
      />

      {/* Tabs */}
      <div
        className="flex-shrink-0 px-5 sm:px-8 pt-3"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <div className="flex gap-0 items-end">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => navigate(TAB_TO_PATH[tab.key])}
                className="flex items-center gap-1.5"
                style={{
                  padding: '8px 16px',
                  border: 0,
                  borderBottom: isActive ? '2px solid var(--accent)' : '2px solid transparent',
                  background: 'transparent',
                  color: isActive ? 'var(--text)' : 'var(--text-3)',
                  fontSize: 13,
                  fontWeight: isActive ? 600 : 400,
                  cursor: 'pointer',
                  transition: 'color 120ms, border-color 120ms',
                  marginBottom: -1,
                }}
              >
                <Icon size={15} strokeWidth={isActive ? 2.2 : 1.8} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Filter bar (Timeline + List) */}
      {(activeTab === 'timeline' || activeTab === 'list') && (
        <div className="flex-shrink-0 px-5 sm:px-8 py-3" style={{ background: 'var(--bg)' }}>
          <div className="flex flex-wrap gap-2 items-center">
            {(['all', 'job', 'project', 'anecdote', 'bullet'] as const).map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className="mono"
                style={{
                  padding: '5px 12px',
                  border: 0,
                  borderRadius: 999,
                  background: filter === f ? 'var(--ink)' : 'transparent',
                  color: filter === f ? 'var(--paper)' : 'var(--text-3)',
                  boxShadow: filter === f ? 'none' : 'inset 0 0 0 1px var(--border-strong)',
                  fontSize: 11,
                  fontWeight: 500,
                  cursor: 'pointer',
                  textTransform: 'capitalize',
                }}
              >
                {f === 'all' ? 'All' : f + 's'}
              </button>
            ))}
            <span className="mono ml-auto" style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}>
              {(activeTab === 'list' ? listView?.length : filtered?.length) ?? 0} ITEMS
            </span>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto px-5 sm:px-8 pb-8 pt-4">
        {error && (
          <div className="card" style={{ padding: 16 }}>Error: {error}</div>
        )}

        {/* Timeline tab */}
        {activeTab === 'timeline' && !error && timelineItems === null && (
          <div className="text-center py-16" style={{ color: 'var(--text-3)' }}>Loading…</div>
        )}

        {activeTab === 'timeline' && !error && timelineItems && timelineItems.length === 0 && (
          <div className="text-center py-16" style={{ color: 'var(--text-4)' }}>
            <p style={{ margin: '0 0 16px', fontSize: 15 }}>No experience items yet.</p>
            <button
              type="button"
              onClick={() => setSelectorOpen(true)}
              className="card card-hover inline-flex items-center gap-2"
              style={{ padding: '10px 18px', border: 0, cursor: 'pointer', fontSize: 13, color: 'var(--text)' }}
            >
              <Plus size={16} strokeWidth={2} />
              Add your first item
            </button>
          </div>
        )}

        {activeTab === 'timeline' && grouped && (
          <div className="relative" style={{ width: '100%' }}>
            {/* Center vertical line */}
            <div className="absolute" style={{ left: '50%', top: 0, bottom: 0, width: 2, marginLeft: -1, background: 'var(--border)' }} />

            {years.map((year, yearIdx) => {
              // Running index across all years keeps left/right alternation continuous.
              const offset = years.slice(0, yearIdx).reduce((n, y) => n + (grouped[y]?.length ?? 0), 0);
              return (
                <div key={year} className="relative" style={{ marginBottom: 40 }}>
                  {/* Year milestone on the line */}
                  <div
                    className="absolute mono flex items-center justify-center"
                    style={{ left: '50%', top: 0, transform: 'translateX(-50%)', padding: '4px 16px', borderRadius: 999, background: 'var(--ink)', color: 'var(--paper)', boxShadow: '0 0 0 3px var(--bg)', fontSize: 12, fontWeight: 700, letterSpacing: '0.04em', zIndex: 3 }}
                  >
                    {year} · {grouped[year].length}
                  </div>

                  <div style={{ paddingTop: 44 }}>
                    {grouped[year].map((item, idx) => {
                      const isLeft = (offset + idx) % 2 === 0;
                      return (
                        <div
                          key={`${item.kind}-${item.id}`}
                          className="relative flex items-start"
                          style={{ marginBottom: 24, flexDirection: isLeft ? 'row' : 'row-reverse' }}
                        >
                          {/* Card side: the whole subtree (children render above the parent) */}
                          <div style={{ width: 'calc(50% - 20px)', position: 'relative' }}>
                            <TreeNode
                              entity={item}
                              depth={0}
                              pathKey={item.id}
                              isRoot
                              isLeft={isLeft}
                              enableChildren={filter === 'all'}
                              connMap={connMap}
                              entityById={entityById}
                              collapsedSet={collapsedSet}
                              ancestry={new Set()}
                              toggle={toggleCollapsed}
                              onClick={handleCardClick}
                            />
                          </div>
                          {/* center gap — the line is absolute; each card draws its own node */}
                          <div style={{ width: 40, flexShrink: 0 }} />
                          {/* empty opposite side (kept clear) */}
                          <div style={{ width: 'calc(50% - 20px)' }} />
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* List tab — nested cards in "all", or a flat list when filtered to one type */}
        {activeTab === 'list' && !error && listView === null && (
          <div className="text-center py-16" style={{ color: 'var(--text-3)' }}>Loading…</div>
        )}

        {activeTab === 'list' && !error && listView && listView.length === 0 && (
          <div className="text-center py-16" style={{ color: 'var(--text-4)' }}>
            <p style={{ margin: '0 0 16px' }}>
              {filter === 'all' ? 'No experience items yet.' : `No ${filter}s yet.`}
            </p>
            <button
              type="button"
              onClick={handleAddForTab}
              className="card card-hover inline-flex items-center gap-2"
              style={{ padding: '10px 18px', border: 0, cursor: 'pointer', fontSize: 13 }}
            >
              <Plus size={16} />
              Add an item
            </button>
          </div>
        )}

        {activeTab === 'list' && timelineItems && listView && listView.length > 0 && (
          <ListTree
            entities={timelineItems}
            connMap={connMap}
            reverseMap={reverseMap}
            entityById={entityById}
            filter={filter}
            onOpen={handleCardClick}
          />
        )}

        {/* Arrange tab — live wiring board over all entities */}
        {activeTab === 'arrange' && !error && timelineItems === null && (
          <div className="text-center py-16" style={{ color: 'var(--text-3)' }}>Loading…</div>
        )}

        {activeTab === 'arrange' && !error && timelineItems && timelineItems.length === 0 && (
          <div className="text-center py-16" style={{ color: 'var(--text-4)' }}>
            <p style={{ margin: '0 0 16px' }}>No experience items to arrange yet.</p>
            <button
              type="button"
              onClick={handleAddForTab}
              className="card card-hover inline-flex items-center gap-2"
              style={{ padding: '10px 18px', border: 0, cursor: 'pointer', fontSize: 13 }}
            >
              <Plus size={16} />
              Add an item
            </button>
          </div>
        )}

        {activeTab === 'arrange' && timelineItems && timelineItems.length > 0 && (
          <ArrangeBoard
            entities={timelineItems}
            connections={connections}
            connection={connectionBundle}
            onChanged={loadTimeline}
            onOpen={handleCardClick}
          />
        )}
      </div>

      {/* Modals */}
      {modalOpen && currentEntityKind === 'job' && (
        <JobModal item={(selected as ExperienceJob)} open={modalOpen} onClose={() => setModalOpen(false)} onSaved={reload} connection={connectionBundle} />
      )}
      {modalOpen && currentEntityKind === 'project' && (
        <ProjectModal item={(selected as ExperienceProject)} open={modalOpen} onClose={() => setModalOpen(false)} onSaved={reload} connection={connectionBundle} />
      )}
      {modalOpen && currentEntityKind === 'anecdote' && (
        <AnecdoteModal item={(selected as ExperienceAnecdote)} open={modalOpen} onClose={() => setModalOpen(false)} onSaved={reload} connection={connectionBundle} />
      )}
      {modalOpen && currentEntityKind === 'bullet' && (
        <BulletModal item={(selected as ExperienceBullet)} open={modalOpen} onClose={() => setModalOpen(false)} onSaved={reload} connection={connectionBundle} />
      )}

      <ImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={reload}
        existingEntities={timelineItems ?? []}
        existingConnections={connectionRefs(connections)}
      />
    </div>
  );
}
