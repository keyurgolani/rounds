import { useEffect, useMemo, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Plus } from 'lucide-react';
import AppHeader from '../components/shell/AppHeader';
import {
  listTimelineEntities,
  createJob,
  createProject,
  createAnecdote,
  createBullet,
  type TimelineEntity,
  type EntityKind,
} from './experienceApi';
import TimelineCard from './TimelineCard';
import EntitySelector from './EntitySelector';
import JobModal from './JobModal';
import ProjectModal from './ProjectModal';
import AnecdoteModal from './AnecdoteModal';
import BulletModal from './BulletModal';

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

export default function ExperienceTimeline() {
  const [items, setItems] = useState<TimelineEntity[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<TimelineEntity | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [filter, setFilter] = useState<string>('all');
  const [selectorOpen, setSelectorOpen] = useState(false);

  const load = useCallback(() => {
    setError(null);
    listTimelineEntities()
      .then(setItems)
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Keep selected item in sync when items refresh (e.g. after edit).
  useEffect(() => {
    if (!selected || !items) return;
    const updated = items.find(
      (i) => i.kind === selected.kind && i.id === selected.id,
    );
    if (updated) setSelected(updated);
  }, [items, selected]);

  const filtered = useMemo(() => {
    if (!items) return null;
    if (filter === 'all') return items;
    return items.filter((i) => i.kind === filter);
  }, [items, filter]);

  const grouped = useMemo(() => {
    if (!filtered) return null;
    return groupByYear(filtered);
  }, [filtered]);

  const years = useMemo(() => {
    if (!grouped) return [];
    return Object.keys(grouped).sort((a, b) => +b - +a);
  }, [grouped]);

  function handleCardClick(item: TimelineEntity) {
    setSelected(item);
    setModalOpen(true);
  }

  async function handleAdd(kind: EntityKind) {
    setSelectorOpen(false);
    const today = new Date().toISOString().split('T')[0];
    let newItem: TimelineEntity;

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

    setItems((prev) => (prev ? [newItem, ...prev] : [newItem]));
    setSelected(newItem);
    setModalOpen(true);
  }

  return (
    <div className="h-full flex flex-col min-h-0">
      <AppHeader
        eyebrow="Track · Experience"
        title="Experience Timeline"
        description="Your career journey: jobs, projects, anecdotes, and achievements."
        chromeActions={
          <div style={{ position: 'relative' }}>
            <button
              type="button"
              onClick={() => setSelectorOpen((v) => !v)}
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

      <div
        className="flex-shrink-0 px-5 sm:px-8 pt-4 pb-2"
        style={{ background: 'var(--bg)' }}
      >
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
          <span
            className="mono ml-auto"
            style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}
          >
            {filtered?.length ?? 0} ITEMS
          </span>
        </div>

        <div className="flex gap-1.5 mt-3">
          {[
            { path: '/experience/anecdotes', label: 'Anecdotes' },
            { path: '/experience/bullets', label: 'Bullets' },
            { path: '/experience/projects', label: 'Projects' },
            { path: '/experience/jobs', label: 'Jobs' },
          ].map((link) => (
            <Link
              key={link.path}
              to={link.path}
              className="mono"
              style={{
                padding: '4px 10px',
                borderRadius: 999,
                background: 'var(--bg-sunken)',
                color: 'var(--text-3)',
                fontSize: 10.5,
                textDecoration: 'none',
                boxShadow: 'inset 0 0 0 1px var(--border)',
              }}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-5 sm:px-8 pb-6 pt-4">
        {error && (
          <div className="card" style={{ padding: 16 }}>
            Error loading experience: {error}
          </div>
        )}
        {!error && items === null && (
          <div className="text-center py-16" style={{ color: 'var(--text-3)' }}>
            Loading…
          </div>
        )}
        {!error && items && items.length === 0 && (
          <div className="text-center py-16" style={{ color: 'var(--text-4)' }}>
            <p style={{ margin: '0 0 16px', fontSize: 15 }}>No experience items yet.</p>
            <button
              type="button"
              onClick={() => setSelectorOpen(true)}
              className="card card-hover inline-flex items-center gap-2"
              style={{
                padding: '10px 18px',
                border: 0,
                cursor: 'pointer',
                fontSize: 13,
                color: 'var(--text)',
              }}
            >
              <Plus size={16} strokeWidth={2} />
              Add your first item
            </button>
          </div>
        )}

        {!error && grouped && (
          <div className="relative mx-auto" style={{ maxWidth: 900 }}>
            {/* Center vertical line */}
            <div
              className="absolute"
              style={{
                left: '50%',
                top: 0,
                bottom: 0,
                width: 2,
                marginLeft: -1,
                background: 'var(--border-strong)',
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
                    width: 48,
                    height: 24,
                    borderRadius: 999,
                    background: 'var(--bg-elev)',
                    boxShadow: 'inset 0 0 0 1px var(--border-strong), 0 0 0 3px var(--bg)',
                    fontSize: 11,
                    fontWeight: 600,
                    color: 'var(--text-2)',
                    zIndex: 2,
                  }}
                >
                  {year}
                </div>

                <div style={{ paddingTop: 36 }}>
                  {grouped[year].map((item, idx) => {
                    const isLeft = idx % 2 === 0;
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
                        <div style={{ width: 'calc(50% - 24px)' }}>
                          <TimelineCard item={item} onClick={() => handleCardClick(item)} />
                        </div>

                        {/* Center node + connector */}
                        <div
                          className="relative flex items-center justify-center flex-shrink-0"
                          style={{ width: 48 }}
                        >
                          {/* Horizontal connector */}
                          <div
                            className="absolute"
                            style={{
                              top: 18,
                              ...(isLeft ? { right: 24 } : { left: 24 }),
                              width: 24,
                              height: 2,
                              background: 'var(--border-strong)',
                            }}
                          />
                          {/* Node dot */}
                          <div
                            style={{
                              width: 10,
                              height: 10,
                              borderRadius: 999,
                              background: 'var(--accent)',
                              border: '2px solid var(--bg)',
                              zIndex: 2,
                              marginTop: 14,
                            }}
                          />
                        </div>

                        {/* Empty side */}
                        <div style={{ width: 'calc(50% - 24px)' }} />
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selected?.kind === 'job' && (
        <JobModal item={selected} open={modalOpen} onClose={() => setModalOpen(false)} onSaved={load} />
      )}
      {selected?.kind === 'project' && (
        <ProjectModal item={selected} open={modalOpen} onClose={() => setModalOpen(false)} onSaved={load} />
      )}
      {selected?.kind === 'anecdote' && (
        <AnecdoteModal item={selected} open={modalOpen} onClose={() => setModalOpen(false)} onSaved={load} />
      )}
      {selected?.kind === 'bullet' && (
        <BulletModal item={selected} open={modalOpen} onClose={() => setModalOpen(false)} onSaved={load} />
      )}
    </div>
  );
}
