import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, ChevronRight, ListTodo } from 'lucide-react';
import { useCampaign } from '../../campaign/CampaignContext';
import MentionText from '../../todos/MentionText';
import { listTodos, updateTodo, type Todo } from '../../todos/api';
import { usePlatform } from '../../hooks/usePlatform';

// A compact "top 5 active todos" card for the dashboard. Overdue
// first, then soonest due, then high priority. Clicking through takes
// the user to /todos; toggling the checkbox marks a todo done in
// place.
export default function TodosWidget() {
  const { currentId } = useCampaign();
  const [todos, setTodos] = useState<Todo[]>([]);
  const [loading, setLoading] = useState(true);
  const { modifierSymbol } = usePlatform();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setTodos(await listTodos(currentId ?? undefined));
    } catch {
      /* silent — widget just stays empty */
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

  const visible = rankTop(todos, 5);

  async function toggle(todo: Todo) {
    const nextCompletedAt = todo.completed_at ? '' : new Date().toISOString();
    setTodos((prev) =>
      prev.map((t) => (t.id === todo.id ? { ...t, completed_at: nextCompletedAt } : t)),
    );
    try {
      await updateTodo(todo.id, { ...todo, completed_at: nextCompletedAt });
    } catch {
      setTodos((prev) =>
        prev.map((t) => (t.id === todo.id ? { ...t, completed_at: todo.completed_at } : t)),
      );
    }
  }

  if (loading && todos.length === 0) return null;

  return (
    <div className="card card-pad-lg flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span
          className="flex items-center gap-1.5"
          style={{ fontSize: 13, fontWeight: 500 }}
        >
          <ListTodo size={13} strokeWidth={1.8} />
          Todos
        </span>
        <Link
          to="/todos"
          className="mono uppercase inline-flex items-center gap-0.5"
          style={{
            fontSize: 10,
            color: 'var(--text-3)',
            letterSpacing: '0.1em',
            textDecoration: 'none',
          }}
        >
          Open todos
          <ChevronRight size={11} strokeWidth={1.7} />
        </Link>
      </div>
      {visible.length === 0 ? (
        <div
          style={{
            fontSize: 12,
            color: 'var(--text-4)',
            fontStyle: 'italic',
            padding: '8px 0',
          }}
        >
          All clear. Hit {modifierSymbol === '⌘' ? '⌘K' : 'Ctrl+K'} to capture a new one.
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          {visible.map((t) => (
            <div
              key={t.id}
              className="flex items-start gap-2"
              style={{
                padding: '8px 10px',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
              }}
            >
              <button
                type="button"
                aria-label="Mark complete"
                onClick={() => toggle(t)}
                style={{
                  marginTop: 1,
                  padding: 0,
                  border: 0,
                  background: 'transparent',
                  color: 'var(--text-4)',
                  cursor: 'pointer',
                }}
              >
                <CheckCircle2 size={15} strokeWidth={1.5} />
              </button>
              <div style={{ minWidth: 0, flex: 1 }}>
                <div
                  style={{
                    fontSize: 12.5,
                    color: 'var(--text)',
                    lineHeight: 1.5,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  <MentionText body={t.body} />
                </div>
              </div>
              {t.due_date && (
                <span
                  className="mono"
                  style={{
                    fontSize: 10.5,
                    color: 'var(--text-4)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {t.due_date}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function rankTop(todos: Todo[], n: number): Todo[] {
  const active = todos.filter((t) => !t.completed_at);
  const now = Date.now();
  return active
    .map((t) => {
      const due = t.due_date ? Date.parse(t.due_date) : NaN;
      const overdue = !Number.isNaN(due) && due < now;
      const dueSoon = !Number.isNaN(due) ? due : Infinity;
      const priority = t.priority === 'high' ? 2 : t.priority === 'low' ? 0 : 1;
      return { t, overdue, dueSoon, priority };
    })
    .sort((a, b) => {
      if (a.overdue !== b.overdue) return a.overdue ? -1 : 1;
      if (a.dueSoon !== b.dueSoon) return a.dueSoon - b.dueSoon;
      return b.priority - a.priority;
    })
    .slice(0, n)
    .map((x) => x.t);
}
