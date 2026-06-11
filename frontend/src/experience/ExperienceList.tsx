import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Plus, ArrowLeft } from 'lucide-react';
import AppHeader from '../components/shell/AppHeader';
import {
  listJobs,
  listProjects,
  listAnecdotes,
  listBullets,
  createJob,
  createProject,
  createAnecdote,
  createBullet,
  type ExperienceJob,
  type ExperienceProject,
  type ExperienceAnecdote,
  type ExperienceBullet,
  type EntityKind,
} from './experienceApi';
import JobModal from './JobModal';
import ProjectModal from './ProjectModal';
import AnecdoteModal from './AnecdoteModal';
import BulletModal from './BulletModal';

interface Props {
  type: EntityKind;
  title: string;
}

const TYPE_SINGULAR: Record<EntityKind, string> = {
  anecdote: 'Anecdote',
  bullet: 'Bullet',
  project: 'Project',
  job: 'Job',
};

type ListItem = ExperienceJob | ExperienceProject | ExperienceAnecdote | ExperienceBullet;

export default function ExperienceList({ type, title }: Props) {
  const [items, setItems] = useState<ListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ListItem | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const load = useCallback(() => {
    setError(null);
    const loader =
      type === 'job'
        ? listJobs()
        : type === 'project'
          ? listProjects()
          : type === 'anecdote'
            ? listAnecdotes()
            : listBullets();
    loader.then(setItems as (v: unknown) => void).catch((e) => setError(String(e)));
  }, [type]);

  useEffect(() => {
    load();
  }, [load]);

  // Keep selected item in sync when items refresh (e.g. after edit).
  useEffect(() => {
    if (!selected || !items) return;
    const updated = items.find((i) => i.id === selected.id);
    if (updated) setSelected(updated);
  }, [items, selected]);

  function handleRowClick(item: ListItem) {
    setSelected(item);
    setModalOpen(true);
  }

  async function handleAdd() {
    const today = new Date().toISOString().split('T')[0];
    let newItem: ListItem;

    switch (type) {
      case 'job':
        newItem = await createJob({ company: 'New Company', role: 'Role', start_date: today });
        break;
      case 'project':
        newItem = await createProject({ title: 'New Project', start_date: today });
        break;
      case 'anecdote':
        newItem = await createAnecdote({ title: 'New Anecdote', date: today });
        break;
      case 'bullet':
        newItem = await createBullet({ title: 'New Bullet', date: today });
        break;
      default:
        throw new Error(`Unknown entity kind: ${type}`);
    }

    setItems((prev) => (prev ? [newItem, ...prev] : [newItem]));
    setSelected(newItem);
    setModalOpen(true);
  }

  function formatDate(item: ListItem): string {
    if ('start_date' in item) {
      const s = new Date(item.start_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      if (!item.end_date) return `${s} – Present`;
      const e = new Date(item.end_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      return `${s} – ${e}`;
    }
    return new Date(item.date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }

  function primaryLabel(item: ListItem): string {
    if ('company' in item && item.company) return item.company;
    return (item as ExperienceProject | ExperienceAnecdote | ExperienceBullet).title;
  }

  function secondaryLabel(item: ListItem): string | undefined {
    if ('role' in item && item.role) return item.role;
    if ('impact' in item && item.impact) return item.impact;
    if ('description' in item && item.description) return item.description;
    return undefined;
  }

  return (
    <div className="h-full flex flex-col min-h-0">
      <AppHeader
        eyebrow="Track · Experience"
        title={title}
        chromeActions={
          <button
            type="button"
            onClick={handleAdd}
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
        }
        compactActions={
          <Link
            to="/experience"
            className="inline-flex items-center gap-1"
            style={{
              fontSize: 12,
              color: 'var(--text-3)',
              textDecoration: 'none',
            }}
          >
            <ArrowLeft size={14} strokeWidth={1.8} />
            Timeline
          </Link>
        }
      />

      <div className="flex-1 min-h-0 overflow-y-auto px-5 sm:px-8 pb-6 pt-4">
        {error && (
          <div className="card" style={{ padding: 16 }}>
            Error: {error}
          </div>
        )}
        {!error && items === null && (
          <div className="text-center py-16" style={{ color: 'var(--text-3)' }}>
            Loading…
          </div>
        )}
        {!error && items && items.length === 0 && (
          <div className="text-center py-16" style={{ color: 'var(--text-4)' }}>
            <p style={{ margin: '0 0 16px' }}>No {title.toLowerCase()} yet.</p>
            <button
              type="button"
              onClick={handleAdd}
              className="card card-hover inline-flex items-center gap-2"
              style={{
                padding: '10px 18px',
                border: 0,
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              <Plus size={16} />
              Add first {TYPE_SINGULAR[type].toLowerCase()}
            </button>
          </div>
        )}

        {!error && items && items.length > 0 && (
          <div className="flex flex-col gap-2">
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => handleRowClick(item)}
                className="card card-hover text-left w-full flex items-center gap-4"
                style={{
                  padding: '12px 16px',
                  background: 'var(--bg-elev)',
                  cursor: 'pointer',
                }}
              >
                <div className="flex-1 min-w-0">
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 500,
                      color: 'var(--text)',
                      marginBottom: 2,
                    }}
                  >
                    {primaryLabel(item)}
                  </div>
                  {secondaryLabel(item) && (
                    <p
                      className="line-clamp-1"
                      style={{
                        fontSize: 12.5,
                        color: 'var(--text-3)',
                        margin: 0,
                      }}
                    >
                      {secondaryLabel(item)}
                    </p>
                  )}
                </div>
                <span className="mono flex-shrink-0" style={{ fontSize: 11, color: 'var(--text-4)' }}>
                  {formatDate(item)}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {selected && type === 'job' && (
        <JobModal item={selected as ExperienceJob} open={modalOpen} onClose={() => setModalOpen(false)} onSaved={load} />
      )}
      {selected && type === 'project' && (
        <ProjectModal item={selected as ExperienceProject} open={modalOpen} onClose={() => setModalOpen(false)} onSaved={load} />
      )}
      {selected && type === 'anecdote' && (
        <AnecdoteModal item={selected as ExperienceAnecdote} open={modalOpen} onClose={() => setModalOpen(false)} onSaved={load} />
      )}
      {selected && type === 'bullet' && (
        <BulletModal item={selected as ExperienceBullet} open={modalOpen} onClose={() => setModalOpen(false)} onSaved={load} />
      )}
    </div>
  );
}
