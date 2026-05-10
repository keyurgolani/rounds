import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import AppHeader from '../../components/shell/AppHeader';
import PageShell from '../../components/shell/PageShell';
import EmptyState from '../../components/shell/EmptyState';
import DifficultyPill from '../../components/shell/DifficultyPill';
import PracticeStatusFilter, {
  type PracticeStatusFilterValue,
} from '../../components/shell/PracticeStatusFilter';
import { effectiveStatus, useStatusMapVersion } from '../../hooks/usePracticeStatus';
import { usePersistedState } from '../../hooks/usePersistedState';
import { listAssignments, type TakeHomeAssignment } from './takeHomeApi';

export default function TakeHomeList() {
  const [items, setItems] = useState<TakeHomeAssignment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = usePersistedState<PracticeStatusFilterValue>(
    'rounds.takeHome.statusFilter',
    'all',
  );
  const statusVersion = useStatusMapVersion();

  useEffect(() => {
    listAssignments().then(setItems).catch((e) => setError(String(e)));
  }, []);

  const filtered = useMemo(() => {
    if (!items) return items;
    if (statusFilter === 'all') return items;
    return items.filter(
      (r) => effectiveStatus('take-home', r.slug) === statusFilter,
    );
    // statusVersion is intentional — see AICodingList for the rationale.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, statusFilter, statusVersion]);

  return (
    <PageShell
      header={
        <AppHeader
          eyebrow="Track 05 · Take-Home Assignments"
          title="Take-Home Assignments"
          description="Realistic engineering prompts with custom-built grading harnesses. Submit and get a deterministic + AI-rubric scorecard."
          chromeActions={
            <PracticeStatusFilter value={statusFilter} onChange={setStatusFilter} />
          }
          compactActions={
            <PracticeStatusFilter value={statusFilter} onChange={setStatusFilter} compact />
          }
        />
      }
    >
      <div className="px-5 sm:px-8 py-6">
        {error && <div className="card" style={{ padding: 16 }}>Error loading assignments: {error}</div>}
        {!error && filtered === null && <div className="text-3">Loading…</div>}
        {!error && filtered?.length === 0 && (
          <EmptyState
            title={
              statusFilter === 'all'
                ? 'No assignments available yet'
                : 'No assignments match that filter'
            }
            body={
              statusFilter === 'all'
                ? 'No take-home assignments are seeded in this workspace yet.'
                : 'Try a different practice-status filter.'
            }
          />
        )}
        {!error && filtered && filtered.length > 0 && (
          <ul className="grid gap-3">
            {filtered.map((a) => (
              <li key={a.id} className="card" style={{ padding: 14 }}>
                <Link to={`/take-home/assignment/${a.slug}`} className="flex items-center gap-3">
                  <DifficultyPill level={a.difficulty} />
                  <span className="font-medium">{a.title}</span>
                  <span className="ml-auto text-3 text-sm">
                    {a.language} · {a.time_budget_min}m
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </PageShell>
  );
}
