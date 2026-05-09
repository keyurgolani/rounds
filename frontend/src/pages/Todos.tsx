import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, Calendar, CheckCircle2, Plus, X } from 'lucide-react';
import { deleteTodo, listTodos, updateTodo, type Todo } from '../todos/api';
import AppHeader from '../components/shell/AppHeader';
import PageShell from '../components/shell/PageShell';
import Select from '../components/shell/Select';
import MentionText from '../todos/MentionText';
import TodoForm, { type TodoFormValue } from '../todos/TodoForm';
import { useCampaign } from '../campaign/CampaignContext';
import { useCommandCenter } from '../command-center/CommandCenterProvider';
import { usePlatform } from '../hooks/usePlatform';
import { usePersistedState } from '../hooks/usePersistedState';

export type { Todo } from '../todos/api';

type Section = 'overdue' | 'today' | 'week' | 'later' | 'no-due' | 'completed';

const SECTION_LABELS: Record<Section, string> = {
  overdue: 'Overdue',
  today: 'Today',
  week: 'This week',
  later: 'Later',
  'no-due': 'No due date',
  completed: 'Completed',
};

type PriorityFilter = 'all' | 'high' | 'normal' | 'low' | 'open' | 'completed';

const PRIORITY_FILTERS: { key: PriorityFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'open', label: 'Open' },
  { key: 'completed', label: 'Done' },
  { key: 'high', label: 'High' },
  { key: 'normal', label: 'Normal' },
  { key: 'low', label: 'Low' },
];

type SortKey =
  | 'due-asc'
  | 'due-desc'
  | 'priority-desc'
  | 'priority-asc'
  | 'created-desc'
  | 'created-asc';

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'due-asc', label: 'Due (soonest first)' },
  { value: 'due-desc', label: 'Due (latest first)' },
  { value: 'priority-desc', label: 'Priority (high first)' },
  { value: 'priority-asc', label: 'Priority (low first)' },
  { value: 'created-desc', label: 'Newest first' },
  { value: 'created-asc', label: 'Oldest first' },
];

function priorityRank(p: string): number {
  if (p === 'high') return 2;
  if (p === 'low') return 0;
  return 1;
}


export default function Todos() {
  const { currentId, currentCampaign } = useCampaign();
  const { modifierSymbol } = usePlatform();
  const cc = useCommandCenter();
  const [todos, setTodos] = useState<Todo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Todo | null>(null);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = usePersistedState<PriorityFilter>('rounds.todos.filter', 'all');
  const [sort, setSort] = usePersistedState<SortKey>('rounds.todos.sort', 'due-asc');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listTodos(currentId ?? undefined);
      setTodos(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load todos.');
    } finally {
      setLoading(false);
    }
  }, [currentId]);

  useEffect(() => {
    void load();
    function onChange() {
      void load();
    }
    window.addEventListener('rounds:todos-changed', onChange);
    return () => window.removeEventListener('rounds:todos-changed', onChange);
  }, [load]);

  async function toggle(todo: Todo) {
    const nextCompletedAt = todo.completed_at ? '' : new Date().toISOString();
    const optimistic = todos.map((t) =>
      t.id === todo.id ? { ...t, completed_at: nextCompletedAt } : t,
    );
    setTodos(optimistic);
    try {
      await updateTodo(todo.id, { ...todo, completed_at: nextCompletedAt });
    } catch {
      setTodos(todos); // revert
    }
  }

  async function saveEdit(value: TodoFormValue) {
    if (!editing) return;
    const updated: Todo = {
      ...editing,
      body: value.body,
      mentions: value.mentions,
      due_date: value.due_date,
      priority: value.priority,
    };
    await updateTodo(editing.id, updated);
    setTodos((prev) => prev.map((t) => (t.id === editing.id ? updated : t)));
    setEditing(null);
    window.dispatchEvent(new CustomEvent('rounds:todos-changed'));
  }

  async function deleteEdit() {
    if (!editing) return;
    const id = editing.id;
    await deleteTodo(id);
    setTodos((prev) => prev.filter((t) => t.id !== id));
    setEditing(null);
    window.dispatchEvent(new CustomEvent('rounds:todos-changed'));
  }

  const filtered = useMemo(() => {
    return todos.filter((t) => {
      if (filter === 'open' && t.completed_at) return false;
      if (filter === 'completed' && !t.completed_at) return false;
      if ((filter === 'high' || filter === 'normal' || filter === 'low') && t.priority !== filter)
        return false;
      if (query.trim()) {
        const s = query.trim().toLowerCase();
        if (!t.body.toLowerCase().includes(s)) return false;
      }
      return true;
    });
  }, [todos, query, filter]);

  const grouped = useMemo(() => groupTodos(filtered, sort), [filtered, sort]);
  const totalMatching = filtered.length;
  const hasData = todos.length > 0;

  return (
    <PageShell
      header={
        <>
          <AppHeader
            eyebrow="Track · Quick capture"
            title="Todos"
            description="Quick notes and follow-ups with @-mentions to questions, categories, applications, rounds, anecdotes, and campaigns."
            chromeActions={
              <button
                type="button"
                onClick={() => cc.openView('add-todo')}
                className="inline-flex items-center gap-1.5"
                style={{
                  padding: '6px 14px',
                  borderRadius: 8,
                  border: 0,
                  background: 'var(--accent)',
                  color: 'var(--bg-elev)',
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
                title={`Add a new todo (${modifierSymbol === '⌘' ? '⌘K' : 'Ctrl+K'})`}
              >
                <Plus size={13} strokeWidth={1.8} />
                Add todo
              </button>
            }
          />
          {hasData && (
            <div
              className="flex-shrink-0 px-5 sm:px-8 pt-4 pb-2"
              style={{ background: 'var(--bg)' }}
            >
              <div className="flex flex-wrap gap-2 items-center">
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search todo body…"
                  className="mono"
                  style={{
                    flex: '1 1 240px',
                    padding: '9px 12px',
                    background: 'var(--bg-elev)',
                    boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                    borderRadius: 'var(--radius)',
                    border: 0,
                    fontSize: 12.5,
                    color: 'var(--text)',
                    outline: 'none',
                  }}
                />
                <div className="flex gap-1.5 flex-wrap">
                  {PRIORITY_FILTERS.map((p) => (
                    <button
                      key={p.key}
                      type="button"
                      onClick={() => setFilter(p.key)}
                      style={{
                        padding: '7px 12px',
                        border: 0,
                        borderRadius: 999,
                        background: filter === p.key ? 'var(--ink)' : 'transparent',
                        color: filter === p.key ? 'var(--paper)' : 'var(--text-3)',
                        boxShadow:
                          filter === p.key
                            ? 'none'
                            : 'inset 0 0 0 1px var(--border-strong)',
                        fontSize: 11.5,
                        fontWeight: 500,
                        cursor: 'pointer',
                      }}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
                <div style={{ minWidth: 200 }}>
                  <Select<SortKey>
                    value={sort}
                    onChange={setSort}
                    options={SORT_OPTIONS}
                    ariaLabel="Sort"
                    align="right"
                  />
                </div>
                <span
                  className="mono ml-auto"
                  style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}
                >
                  {totalMatching} OF {todos.length} TODOS
                </span>
              </div>
            </div>
          )}
        </>
      }
    >
      <div className="px-5 sm:px-8 py-5 flex flex-col gap-6">
        {error && (
          <div className="card p-3" style={{ color: 'var(--plum)', fontSize: 13 }}>
            {error}
          </div>
        )}
        {loading && todos.length === 0 && (
          <div
            className="card p-8 text-center"
            style={{ color: 'var(--text-4)', fontSize: 13 }}
          >
            Loading…
          </div>
        )}
        {!loading && todos.length === 0 && (
          <div
            className="card p-8 text-center"
            style={{ color: 'var(--text-3)', fontSize: 13 }}
          >
            No todos yet. Hit <span className="mono">{modifierSymbol === '⌘' ? '⌘K' : 'Ctrl+K'}</span> anywhere to capture one.
          </div>
        )}

        {(['overdue', 'today', 'week', 'later', 'no-due', 'completed'] as Section[]).map(
          (sec) => {
            const items = grouped[sec];
            if (!items || items.length === 0) return null;
            return (
              <section key={sec}>
                <div
                  className="eyebrow mb-2 flex items-center gap-1.5"
                  style={{
                    color: sec === 'overdue' ? 'var(--plum)' : undefined,
                  }}
                >
                  {sec === 'overdue' && <AlertCircle size={11} strokeWidth={1.8} />}
                  {SECTION_LABELS[sec]}
                  <span
                    className="mono"
                    style={{ color: 'var(--text-4)', marginLeft: 4 }}
                  >
                    {items.length}
                  </span>
                </div>
                <ol
                  className="flex flex-col gap-2"
                  style={{ listStyle: 'none', padding: 0, margin: 0 }}
                >
                  {items.map((t) => (
                    <TodoRow
                      key={t.id}
                      todo={t}
                      onToggle={() => toggle(t)}
                      onOpen={() => setEditing(t)}
                    />
                  ))}
                </ol>
              </section>
            );
          },
        )}
      </div>

      {editing && (
        <EditModal
          todo={editing}
          campaignName={currentCampaign?.name}
          onSubmit={saveEdit}
          onDelete={deleteEdit}
          onClose={() => setEditing(null)}
        />
      )}
    </PageShell>
  );
}

function TodoRow({
  todo,
  onToggle,
  onOpen,
}: {
  todo: Todo;
  onToggle: () => void;
  onOpen: () => void;
}) {
  const done = !!todo.completed_at;
  const body = todo.body;
  return (
    <li
      className="card card-hover"
      onClick={onOpen}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onOpen();
        }
      }}
      style={{
        padding: '12px 14px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: 10,
        opacity: done ? 0.6 : 1,
        cursor: 'pointer',
      }}
    >
      <button
        type="button"
        aria-label={done ? 'Mark incomplete' : 'Mark complete'}
        onClick={(e) => {
          e.stopPropagation();
          onToggle();
        }}
        style={{
          marginTop: 1,
          padding: 0,
          border: 0,
          background: 'transparent',
          color: done ? 'var(--forest)' : 'var(--text-4)',
          cursor: 'pointer',
          flexShrink: 0,
        }}
      >
        <CheckCircle2 size={18} strokeWidth={done ? 2.2 : 1.4} />
      </button>
      <div style={{ minWidth: 0, flex: 1 }}>
        <div
          className="flex items-start gap-2 flex-wrap"
          style={{
            fontSize: 13.5,
            color: done ? 'var(--text-3)' : 'var(--text)',
            textDecoration: done ? 'line-through' : 'none',
            lineHeight: 1.55,
          }}
        >
          <MentionText body={body} style={{ flex: 1, minWidth: 0 }} />
          {todo.priority === 'high' && <PriorityPill tone="plum">high</PriorityPill>}
          {todo.priority === 'low' && <PriorityPill tone="muted">low</PriorityPill>}
        </div>
        {todo.due_date && (
          <div
            className="mono flex items-center gap-1.5 mt-1.5"
            style={{ fontSize: 10.5, color: 'var(--text-4)' }}
          >
            <Calendar size={10} strokeWidth={1.8} />
            {todo.due_date}
          </div>
        )}
      </div>
    </li>
  );
}

function PriorityPill({
  tone,
  children,
}: {
  tone: 'plum' | 'muted';
  children: React.ReactNode;
}) {
  const c =
    tone === 'plum'
      ? { bg: 'var(--plum-soft)', fg: 'var(--plum)' }
      : { bg: 'var(--paper-3)', fg: 'var(--text-3)' };
  return (
    <span className="pill" style={{ background: c.bg, color: c.fg, fontSize: 10 }}>
      {children}
    </span>
  );
}

function EditModal({
  todo,
  campaignName,
  onSubmit,
  onDelete,
  onClose,
}: {
  todo: Todo;
  campaignName?: string;
  onSubmit: (value: TodoFormValue) => Promise<void>;
  onDelete: () => Promise<void>;
  onClose: () => void;
}) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Edit todo"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(24,22,19,0.35)',
        backdropFilter: 'blur(2px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
        zIndex: 100,
      }}
    >
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 480,
          maxWidth: '100%',
          padding: 14,
          boxShadow: 'var(--shadow-elev)',
          maxHeight: 'calc(100vh - 32px)',
          overflowY: 'auto',
        }}
      >
        <div className="flex items-center justify-between mb-2">
          <div className="eyebrow">Edit todo</div>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            style={{
              padding: 4,
              border: 0,
              background: 'transparent',
              color: 'var(--text-3)',
              cursor: 'pointer',
            }}
          >
            <X size={13} strokeWidth={1.7} />
          </button>
        </div>
        <TodoForm
          initial={{
            body: todo.body,
            due_date: todo.due_date,
            priority: todo.priority,
          }}
          onSubmit={onSubmit}
          onDelete={onDelete}
          onCancel={onClose}
          campaignName={campaignName}
          submitLabel="Save"
        />
      </div>
    </div>
  );
}

function groupTodos(todos: Todo[], sort: SortKey = 'due-asc'): Record<Section, Todo[]> {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const week = new Date(today);
  week.setDate(week.getDate() + 7);

  const g: Record<Section, Todo[]> = {
    overdue: [],
    today: [],
    week: [],
    later: [],
    'no-due': [],
    completed: [],
  };

  for (const t of todos) {
    if (t.completed_at) {
      g.completed.push(t);
      continue;
    }
    if (!t.due_date) {
      g['no-due'].push(t);
      continue;
    }
    const d = new Date(t.due_date);
    if (Number.isNaN(d.getTime())) {
      g['no-due'].push(t);
      continue;
    }
    d.setHours(0, 0, 0, 0);
    if (d < today) g.overdue.push(t);
    else if (d.getTime() === today.getTime()) g.today.push(t);
    else if (d < week) g.week.push(t);
    else g.later.push(t);
  }

  const cmp = (a: Todo, b: Todo) => {
    switch (sort) {
      case 'due-desc':
        return (b.due_date || '').localeCompare(a.due_date || '');
      case 'priority-desc':
        return priorityRank(b.priority) - priorityRank(a.priority);
      case 'priority-asc':
        return priorityRank(a.priority) - priorityRank(b.priority);
      case 'created-desc':
        return (b.created_at || '').localeCompare(a.created_at || '');
      case 'created-asc':
        return (a.created_at || '').localeCompare(b.created_at || '');
      case 'due-asc':
      default:
        return (a.due_date || '').localeCompare(b.due_date || '');
    }
  };

  for (const sec of ['overdue', 'today', 'week', 'later', 'no-due'] as Section[]) {
    g[sec].sort(cmp);
  }
  g.completed.sort((a, b) => (b.completed_at || '').localeCompare(a.completed_at || ''));

  return g;
}

