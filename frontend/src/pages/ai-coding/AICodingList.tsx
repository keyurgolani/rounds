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
import { listRounds, type AICodingRound } from './aiCodingApi';

export default function AICodingList() {
  const [rounds, setRounds] = useState<AICodingRound[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = usePersistedState<PracticeStatusFilterValue>(
    'rounds.aiCoding.statusFilter',
    'all',
  );
  // Mirrors CodingList: status changes elsewhere bump a version counter
  // so the memoized filter re-runs even though `effectiveStatus` reads
  // from a module-level cache rather than React state.
  const statusVersion = useStatusMapVersion();

  useEffect(() => {
    listRounds().then(setRounds).catch((e) => setError(String(e)));
  }, []);

  const filtered = useMemo(() => {
    if (!rounds) return rounds;
    if (statusFilter === 'all') return rounds;
    return rounds.filter((r) => effectiveStatus('ai-coding', r.slug) === statusFilter);
    // statusVersion is intentional — see comment above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rounds, statusFilter, statusVersion]);

  return (
    <PageShell
      header={
        <AppHeader
          eyebrow="Track 04 · AI Assisted Coding"
          title="AI Assisted Coding"
          description="Multi-file rounds with an AI pair. Bug-fix, feature, and optimize checkpoints — graded on deterministic tests plus a rubric review."
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
        {error && <div className="card" style={{ padding: 16 }}>Error loading rounds: {error}</div>}
        {!error && filtered === null && <div className="text-3">Loading…</div>}
        {!error && filtered?.length === 0 && (
          <EmptyState
            title={
              statusFilter === 'all'
                ? 'No rounds available yet'
                : 'No rounds match that filter'
            }
            body={
              statusFilter === 'all'
                ? 'No AI-coding rounds are seeded in this workspace yet.'
                : 'Try a different practice-status filter.'
            }
          />
        )}
        {!error && filtered && filtered.length > 0 && (
          <ul className="grid gap-3">
            {filtered.map((r) => (
              <li key={r.id} className="card" style={{ padding: 14 }}>
                <Link to={`/ai-coding/round/${r.slug}`} className="flex items-center gap-3">
                  <DifficultyPill level={r.difficulty} />
                  <span className="font-medium">{r.title}</span>
                  <span className="ml-auto text-3 text-sm">{r.language}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </PageShell>
  );
}
