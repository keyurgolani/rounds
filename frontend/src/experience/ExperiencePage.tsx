import { useState, useCallback, useEffect, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Briefcase,
  FolderKanban,
  MessageSquareQuote,
  ListChecks,
  Clock,
  Plus,
  Upload,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import AppHeader from '../components/shell/AppHeader';
import {
  listTimelineEntities,
  listJobs,
  listProjects,
  listAnecdotes,
  listBullets,
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
import EntitySelector from './EntitySelector';
import ImportModal from './ImportModal';
import JobModal from './JobModal';
import ProjectModal from './ProjectModal';
import AnecdoteModal from './AnecdoteModal';
import BulletModal from './BulletModal';

// ---------------------------------------------------------------------------
// Tab definitions
// ---------------------------------------------------------------------------

const TABS = [
  { key: 'timeline' as const, label: 'Timeline', icon: Clock },
  { key: 'anecdote' as const, label: 'Anecdotes', icon: MessageSquareQuote },
  { key: 'bullet' as const, label: 'Bullets', icon: ListChecks },
  { key: 'project' as const, label: 'Projects', icon: FolderKanban },
  { key: 'job' as const, label: 'Jobs', icon: Briefcase },
] as const;

type TabKey = (typeof TABS)[number]['key'];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function groupByYear(items: TimelineEntity[]): Record<string, TimelineEntity[]> {
  const groups: Record<string, TimelineEntity[]> = {};
  for (const item of items) {
    const date = item.kind === 'job' || item.kind === 'project' ? item.start_date : item.date;
    const year = new Date(date).getFullYear().toString();
    if (!groups[year]) groups[year] = [];
    groups[year].push(item);
  }
  for (const year of Object.keys(groups)) {
    groups[year].sort((a, b) => {
      const dateA = a.kind === 'job' || a.kind === 'project' ? a.start_date : a.date;
      const dateB = b.kind === 'job' || b.kind === 'project' ? b.start_date : b.date;
      return +new Date(dateB) - +new Date(dateA);
    });
  }
  return groups;
}

// ---------------------------------------------------------------------------
// Timeline card
// ---------------------------------------------------------------------------

const TYPE_COLORS: Record<TimelineEntity['kind'], { bg: string; text: string; dot: string }> = {
  anecdote: { bg: 'var(--accent-soft)', text: 'var(--accent)', dot: 'var(--accent)' },
  bullet: { bg: 'var(--forest-soft)', text: 'var(--forest)', dot: 'var(--forest)' },
  project: { bg: 'var(--ochre-soft)', text: 'var(--ochre)', dot: 'var(--ochre)' },
  job: { bg: 'var(--ink-soft)', text: 'var(--ink)', dot: 'var(--ink)' },
};

const TYPE_LABELS: Record<TimelineEntity['kind'], string> = {
  anecdote: 'Anecdote',
  bullet: 'Bullet',
  project: 'Project',
  job: 'Job',
};

function formatDate(entity: TimelineEntity): string {
  if (entity.kind === 'job' || entity.kind === 'project') {
    const s = new Date(entity.start_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    if (!entity.end_date) return `${s} – Present`;
    const e = new Date(entity.end_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    return `${s} – ${e}`;
  }
  return new Date(entity.date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

// ---------------------------------------------------------------------------
// Nested children (timeline)
// ---------------------------------------------------------------------------

// Child kinds in render order — the more granular, the more minimal the card.
const CHILD_KINDS: EntityKind[] = ['project', 'anecdote', 'bullet'];

function childIdsOf(map: ConnectionMap, parentId: string): { kind: EntityKind; id: string }[] {
  const entry = map[parentId];
  if (!entry) return [];
  return CHILD_KINDS.flatMap((kind) => (entry[kind] ?? []).map((id) => ({ kind, id })));
}

function hasChildren(map: ConnectionMap, parentId: string): boolean {
  const entry = map[parentId];
  if (!entry) return false;
  return CHILD_KINDS.some((kind) => (entry[kind] ?? []).length > 0);
}

interface NestedProps {
  /** Junction lookup id (the actual entity id). */
  lookupId: string;
  /** Unique render path key so the same entity expands independently under each parent. */
  pathKey: string;
  connMap: ConnectionMap;
  entityById: Record<string, TimelineEntity>;
  expandedSet: Set<string>;
  toggle: (key: string) => void;
  onClick: (entity: TimelineEntity) => void;
}

/** Renders the list of children connected under a given parent. */
function ChildList({ lookupId, pathKey, connMap, entityById, expandedSet, toggle, onClick }: NestedProps) {
  const children = childIdsOf(connMap, lookupId);
  if (children.length === 0) return null;
  return (
    <div
      className="flex flex-col"
      style={{ gap: 6, marginTop: 8, paddingLeft: 12, borderLeft: '1px dashed var(--border)' }}
    >
      {children.map(({ id }) => {
        const child = entityById[id];
        if (!child) return null;
        return (
          <ChildCard
            key={`${pathKey}>${id}`}
            entity={child}
            pathKey={`${pathKey}>${id}`}
            connMap={connMap}
            entityById={entityById}
            expandedSet={expandedSet}
            toggle={toggle}
            onClick={onClick}
          />
        );
      })}
    </div>
  );
}

interface ChildCardProps {
  entity: TimelineEntity;
  pathKey: string;
  connMap: ConnectionMap;
  entityById: Record<string, TimelineEntity>;
  expandedSet: Set<string>;
  toggle: (key: string) => void;
  onClick: (entity: TimelineEntity) => void;
}

/** A single nested child card, minimal in proportion to its granularity. */
function ChildCard({ entity, pathKey, connMap, entityById, expandedSet, toggle, onClick }: ChildCardProps) {
  const colors = TYPE_COLORS[entity.kind];
  const expandable = hasChildren(connMap, entity.id);
  const isExpanded = expandedSet.has(pathKey);

  const padding =
    entity.kind === 'project' ? '12px 16px' : entity.kind === 'anecdote' ? '8px 14px' : '6px 14px';

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => onClick(entity)}
        onKeyDown={(e) => { if (e.key === 'Enter') onClick(entity); }}
        style={{
          padding,
          borderLeft: `2px solid ${colors.text}`,
          borderRadius: 'var(--radius)',
          background: 'var(--bg)',
          boxShadow: 'inset 0 0 0 1px var(--border)',
          cursor: 'pointer',
        }}
      >
        {entity.kind === 'bullet' ? (
          <span style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.4 }}>
            • {entity.title}
            {entity.impact ? <span style={{ color: 'var(--text-4)' }}> ({entity.impact})</span> : null}
          </span>
        ) : (
          <>
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className="pill mono"
                style={{ fontSize: 8.5, letterSpacing: '0.06em', background: colors.bg, color: colors.text, padding: '1px 6px' }}
              >
                {TYPE_LABELS[entity.kind].toUpperCase()}
              </span>
              <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>{formatDate(entity)}</span>
              {expandable && (
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); toggle(pathKey); }}
                  className="flex items-center gap-0.5 ml-auto"
                  style={{ background: 0, border: 0, cursor: 'pointer', color: 'var(--text-3)', fontSize: 10, padding: 0 }}
                >
                  {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                </button>
              )}
            </div>
            <div style={{ fontSize: entity.kind === 'project' ? 14 : 13, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3, marginTop: 3 }}>
              {entity.kind === 'job' ? entity.company : entity.title}
            </div>
            {entity.kind === 'project' && (entity.company || entity.role) && (
              <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 1 }}>
                {[entity.company, entity.role].filter(Boolean).join(' · ')}
              </div>
            )}
          </>
        )}
      </div>
      {expandable && isExpanded && (
        <div style={{ marginLeft: 8 }}>
          <ChildList
            lookupId={entity.id}
            pathKey={pathKey}
            connMap={connMap}
            entityById={entityById}
            expandedSet={expandedSet}
            toggle={toggle}
            onClick={onClick}
          />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

const PATH_TO_TAB: Record<string, TabKey> = {
  '/experience': 'timeline',
  '/experience/anecdotes': 'anecdote',
  '/experience/bullets': 'bullet',
  '/experience/projects': 'project',
  '/experience/jobs': 'job',
};

const TAB_TO_PATH: Record<TabKey, string> = {
  timeline: '/experience',
  anecdote: '/experience/anecdotes',
  bullet: '/experience/bullets',
  project: '/experience/projects',
  job: '/experience/jobs',
};

export default function ExperiencePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const activeTab = PATH_TO_TAB[location.pathname] ?? 'timeline';
  const [timelineItems, setTimelineItems] = useState<TimelineEntity[] | null>(null);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [expandedSet, setExpandedSet] = useState<Set<string>>(new Set());
  const [listItems, setListItems] = useState<(ExperienceJob | ExperienceProject | ExperienceAnecdote | ExperienceBullet)[] | null>(null);
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

  const toggleExpanded = useCallback((key: string) => {
    setExpandedSet((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  // Load list data for current tab
  const loadList = useCallback(() => {
    if (activeTab === 'timeline') return;
    setError(null);
    const loader =
      activeTab === 'job' ? listJobs()
        : activeTab === 'project' ? listProjects()
          : activeTab === 'anecdote' ? listAnecdotes()
            : listBullets();
    loader.then((v) => setListItems(v as (ExperienceJob | ExperienceProject | ExperienceAnecdote | ExperienceBullet)[]))
      .catch((e) => setError(String(e)));
  }, [activeTab]);

  useEffect(() => {
    // Always load timeline entities + connections — they back the entity lookup,
    // connection maps, and modal navigation used on every tab.
    loadTimeline();
    if (activeTab !== 'timeline') loadList();
  }, [activeTab, loadTimeline, loadList]);

  // Sync selected after refresh
  useEffect(() => {
    if (!selected) return;
    const items = activeTab === 'timeline' ? timelineItems : listItems;
    if (!items) return;
    const updated = items.find((i) => i.id === selected.id);
    if (updated) setSelected(updated);
  }, [timelineItems, listItems, selected, activeTab]);

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
    return groupByYear(filtered);
  }, [filtered]);

  const years = useMemo(() => {
    if (!grouped) return [];
    return Object.keys(grouped).sort((a, b) => +b - +a);
  }, [grouped]);

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

    if (activeTab === 'timeline') {
      setTimelineItems((prev) => (prev ? [newItem as TimelineEntity, ...prev] : [newItem as TimelineEntity]));
    } else {
      setListItems((prev) => (prev ? [newItem, ...prev] : [newItem]));
    }
    setSelected(newItem);
    setModalOpen(true);
  }

  async function handleAddForTab() {
    if (activeTab === 'timeline') {
      setSelectorOpen(true);
      return;
    }
    await handleAdd(activeTab as EntityKind);
  }

  function reload() {
    loadTimeline();
    if (activeTab !== 'timeline') loadList();
  }

  function listFormatDate(item: ExperienceJob | ExperienceProject | ExperienceAnecdote | ExperienceBullet): string {
    if ('start_date' in item) {
      const s = new Date(item.start_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      if (!item.end_date) return `${s} – Present`;
      const e = new Date(item.end_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      return `${s} – ${e}`;
    }
    return new Date((item as ExperienceAnecdote | ExperienceBullet).date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }

  function listPrimary(item: ExperienceJob | ExperienceProject | ExperienceAnecdote | ExperienceBullet): string {
    if ('company' in item && 'employment_type' in item) {
      if (item.company) return item.company;
    }
    return (item as ExperienceProject | ExperienceAnecdote | ExperienceBullet).title || (item as ExperienceJob).company;
  }

  function listSecondary(item: ExperienceJob | ExperienceProject | ExperienceAnecdote | ExperienceBullet): string | undefined {
    if ('role' in item && item.role) return item.role;
    if ('impact' in item && item.impact) return item.impact;
    if ('description' in item && (item as ExperienceProject).description) return (item as ExperienceProject).description;
    return undefined;
  }

  // Prefer the selected entity's own kind (set on every TimelineEntity, including
  // those reached via connection navigation); fall back to the active list tab.
  const currentEntityKind: EntityKind | undefined =
    selected && 'kind' in selected
      ? (selected as TimelineEntity).kind
      : activeTab !== 'timeline'
        ? (activeTab as EntityKind)
        : undefined;

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

      {/* Filter bar (timeline only) */}
      {activeTab === 'timeline' && (
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
              {filtered?.length ?? 0} ITEMS
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
          <div className="relative mx-auto" style={{ maxWidth: 1100 }}>
            {/* Center vertical line */}
            <div
              className="absolute"
              style={{
                left: '50%',
                top: 0,
                bottom: 0,
                width: 2,
                marginLeft: -1,
                background: 'var(--border)',
              }}
            />

            {years.map((year) => (
              <div key={year} className="relative" style={{ marginBottom: 40 }}>
                {/* Year milestone on the line */}
                <div
                  className="absolute mono flex items-center justify-center"
                  style={{
                    left: '50%',
                    top: 0,
                    transform: 'translateX(-50%)',
                    padding: '4px 16px',
                    borderRadius: 999,
                    background: 'var(--ink)',
                    color: 'var(--paper)',
                    boxShadow: '0 0 0 3px var(--bg)',
                    fontSize: 12,
                    fontWeight: 700,
                    letterSpacing: '0.04em',
                    zIndex: 2,
                  }}
                >
                  {year} · {grouped[year].length}
                </div>

                <div style={{ paddingTop: 36 }}>
                  {grouped[year].map((item, idx) => {
                    const isLeft = idx % 2 === 0;
                    const colors = TYPE_COLORS[item.kind];
                    const title = item.kind === 'job' ? item.company : item.title;
                    const subtitle = item.kind === 'job' ? item.role : item.kind === 'project' ? `${item.company ? item.company + ' · ' : ''}${item.role || ''}` : undefined;

                    return (
                      <div
                        key={`${item.kind}-${item.id}`}
                        className="relative flex items-start"
                        style={{
                          marginBottom: 16,
                          flexDirection: isLeft ? 'row' : 'row-reverse',
                        }}
                      >
                        {/* Card side */}
                        <div style={{ width: 'calc(50% - 20px)' }}>
                          <button
                            type="button"
                            onClick={() => handleCardClick(item)}
                            className="text-left w-full"
                            style={{
                              padding: '16px 20px',
                              borderLeft: isLeft ? 'none' : `3px solid ${colors.text}`,
                              borderRight: isLeft ? `3px solid ${colors.text}` : 'none',
                              borderRadius: 'var(--radius)',
                              background: 'var(--bg-elev)',
                              boxShadow: 'inset 0 0 0 1px var(--border)',
                              cursor: 'pointer',
                              transition: 'box-shadow 120ms, transform 120ms',
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.boxShadow = `inset 0 0 0 1px var(--border), 0 4px 12px rgba(0,0,0,0.1)`;
                              e.currentTarget.style.transform = 'translateY(-1px)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.boxShadow = 'inset 0 0 0 1px var(--border)';
                              e.currentTarget.style.transform = 'translateY(0)';
                            }}
                          >
                            <div className="flex items-center gap-2 flex-wrap" style={{ marginBottom: 6 }}>
                              <span
                                className="pill mono"
                                style={{
                                  fontSize: 9,
                                  letterSpacing: '0.08em',
                                  background: colors.bg,
                                  color: colors.text,
                                  padding: '2px 8px',
                                }}
                              >
                                {TYPE_LABELS[item.kind].toUpperCase()}
                              </span>
                              <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
                                {formatDate(item)}
                              </span>
                            </div>

                            <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3, marginBottom: subtitle || (item.kind !== 'bullet' && 'description' in item && item.description) ? 4 : 0 }}>
                              {title}
                            </div>

                            {subtitle && (
                              <div style={{ fontSize: 13, color: 'var(--text-2)', marginTop: 2 }}>
                                {subtitle}
                              </div>
                            )}

                            {item.kind !== 'bullet' && 'description' in item && item.description && (
                              <p className="line-clamp-2" style={{ fontSize: 13, color: 'var(--text-3)', lineHeight: 1.5, margin: '6px 0 0' }}>
                                {item.description}
                              </p>
                            )}

                            {item.kind === 'bullet' && item.impact && (
                              <p style={{ fontSize: 13, color: 'var(--text-3)', margin: '4px 0 0', lineHeight: 1.5 }}>
                                {item.impact}
                              </p>
                            )}

                            {item.tags.length > 0 && (
                              <div className="flex flex-wrap gap-1" style={{ marginTop: 8 }}>
                                {item.tags.slice(0, 6).map((tag) => (
                                  <span
                                    key={tag}
                                    className="pill"
                                    style={{
                                      fontSize: 10,
                                      background: 'transparent',
                                      color: 'var(--text-4)',
                                      boxShadow: 'inset 0 0 0 1px var(--border)',
                                      padding: '1px 7px',
                                    }}
                                  >
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}
                          </button>

                          {/* Nested connected children */}
                          {filter === 'all' && hasChildren(connMap, item.id) && (
                            <div style={{ marginTop: 6 }}>
                              <button
                                type="button"
                                onClick={() => toggleExpanded(item.id)}
                                className="flex items-center gap-1"
                                style={{ background: 0, border: 0, cursor: 'pointer', color: 'var(--text-3)', fontSize: 11, padding: '2px 0' }}
                              >
                                {expandedSet.has(item.id) ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                                {childIdsOf(connMap, item.id).length} linked
                              </button>
                              {expandedSet.has(item.id) && (
                                <ChildList
                                  lookupId={item.id}
                                  pathKey={item.id}
                                  connMap={connMap}
                                  entityById={entityById}
                                  expandedSet={expandedSet}
                                  toggle={toggleExpanded}
                                  onClick={handleCardClick}
                                />
                              )}
                            </div>
                          )}
                        </div>

                        {/* Center node + connector */}
                        <div
                          className="relative flex items-center justify-center flex-shrink-0"
                          style={{ width: 40 }}
                        >
                          {/* Horizontal connector */}
                          <div
                            className="absolute"
                            style={{
                              top: 20,
                              ...(isLeft ? { right: 20 } : { left: 20 }),
                              width: 20,
                              height: 2,
                              background: colors.text,
                              opacity: 0.4,
                            }}
                          />
                          {/* Node dot */}
                          <div
                            style={{
                              width: 10,
                              height: 10,
                              borderRadius: 999,
                              background: colors.text,
                              border: '2px solid var(--bg)',
                              zIndex: 2,
                              marginTop: 16,
                            }}
                          />
                        </div>

                        {/* Empty side */}
                        <div style={{ width: 'calc(50% - 20px)' }} />
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* List tab (anecdotes, bullets, projects, jobs) */}
        {activeTab !== 'timeline' && !error && listItems === null && (
          <div className="text-center py-16" style={{ color: 'var(--text-3)' }}>Loading…</div>
        )}

        {activeTab !== 'timeline' && !error && listItems && listItems.length === 0 && (
          <div className="text-center py-16" style={{ color: 'var(--text-4)' }}>
            <p style={{ margin: '0 0 16px' }}>No {activeTab}s yet.</p>
            <button
              type="button"
              onClick={handleAddForTab}
              className="card card-hover inline-flex items-center gap-2"
              style={{ padding: '10px 18px', border: 0, cursor: 'pointer', fontSize: 13 }}
            >
              <Plus size={16} />
              Add first {activeTab}
            </button>
          </div>
        )}

        {activeTab !== 'timeline' && listItems && listItems.length > 0 && (
          <div className="flex flex-col gap-2">
            {listItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => handleCardClick(item)}
                className="text-left w-full flex items-center gap-4"
                style={{
                  padding: '14px 18px',
                  borderRadius: 'var(--radius)',
                  background: 'var(--bg-elev)',
                  boxShadow: 'inset 0 0 0 1px var(--border)',
                  cursor: 'pointer',
                  transition: 'box-shadow 120ms',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = `inset 0 0 0 1px var(--border), 0 2px 8px rgba(0,0,0,0.08)`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = 'inset 0 0 0 1px var(--border)';
                }}
              >
                <div className="flex-1 min-w-0">
                  <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text)', marginBottom: 2 }}>
                    {listPrimary(item)}
                  </div>
                  {listSecondary(item) && (
                    <p className="line-clamp-1" style={{ fontSize: 12.5, color: 'var(--text-3)', margin: 0 }}>
                      {listSecondary(item)}
                    </p>
                  )}
                </div>
                {hasChildren(connMap, item.id) && (
                  <span
                    className="mono pill flex-shrink-0"
                    style={{ fontSize: 10, background: 'var(--bg-sunken)', color: 'var(--text-3)', padding: '2px 8px', boxShadow: 'inset 0 0 0 1px var(--border)' }}
                  >
                    {childIdsOf(connMap, item.id).length} linked
                  </span>
                )}
                <span className="mono flex-shrink-0" style={{ fontSize: 11, color: 'var(--text-4)' }}>
                  {listFormatDate(item)}
                </span>
              </button>
            ))}
          </div>
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
