import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import AppHeader from '../../components/shell/AppHeader';
import DifficultyPill from '../../components/shell/DifficultyPill';
import StatusDot from '../../components/shell/StatusDot';
import Select from '../../components/shell/Select';
import PracticeStatusFilter, {
  type PracticeStatusFilterValue,
} from '../../components/shell/PracticeStatusFilter';
import { effectiveStatus, useStatusMapVersion } from '../../hooks/usePracticeStatus';
import { useInfiniteList } from '../../hooks/useInfiniteList';
import { usePersistedState } from '../../hooks/usePersistedState';
import { listRounds, type AICodingRound } from './aiCodingApi';

type SortKey =
  | 'title-asc'
  | 'title-desc'
  | 'difficulty-easy'
  | 'difficulty-hard';

const DIFFICULTY_RANK: Record<string, number> = {
  easy: 0,
  Easy: 0,
  medium: 1,
  Medium: 1,
  hard: 2,
  Hard: 2,
};

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'title-asc', label: 'Title (A–Z)' },
  { value: 'title-desc', label: 'Title (Z–A)' },
  { value: 'difficulty-easy', label: 'Difficulty (Easy first)' },
  { value: 'difficulty-hard', label: 'Difficulty (Hard first)' },
];

const ALL_OPTION = '__all__';

function stripMarkdown(s: string): string {
  return s
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`[^`]*`/g, '')
    .replace(/[#*_>~]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

export default function AICodingList() {
  const [rounds, setRounds] = useState<AICodingRound[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [difficulty, setDifficulty] = usePersistedState<string | null>(
    'rounds.aiCoding.difficulty',
    null,
  );
  const [topic, setTopic] = usePersistedState<string>('rounds.aiCoding.topic', ALL_OPTION);
  const [language, setLanguage] = usePersistedState<string>(
    'rounds.aiCoding.language',
    ALL_OPTION,
  );
  const [sort, setSort] = usePersistedState<SortKey>('rounds.aiCoding.sort', 'title-asc');
  const [statusFilter, setStatusFilter] = usePersistedState<PracticeStatusFilterValue>(
    'rounds.aiCoding.statusFilter',
    'all',
  );
  const statusVersion = useStatusMapVersion();

  useEffect(() => {
    listRounds()
      .then(setRounds)
      .catch((e) => setError(String(e)));
  }, []);

  const allTopics = useMemo(() => {
    const set = new Set<string>();
    for (const r of rounds ?? []) for (const t of r.topics ?? []) set.add(t);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [rounds]);

  const allLanguages = useMemo(() => {
    const set = new Set<string>();
    for (const r of rounds ?? []) if (r.language) set.add(r.language);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [rounds]);

  const filtered = useMemo(() => {
    if (!rounds) return null;
    const matches = rounds.filter((r) => {
      if (difficulty && r.difficulty.toLowerCase() !== difficulty.toLowerCase()) return false;
      if (topic !== ALL_OPTION && !(r.topics ?? []).includes(topic)) return false;
      if (language !== ALL_OPTION && r.language !== language) return false;
      if (statusFilter !== 'all' && effectiveStatus('ai-coding', r.slug) !== statusFilter) {
        return false;
      }
      if (query.trim()) {
        const s = query.trim().toLowerCase();
        const blob = `${r.title} ${(r.topics ?? []).join(' ')} ${(r.companies ?? []).join(' ')} ${r.description ?? ''}`.toLowerCase();
        if (!blob.includes(s)) return false;
      }
      return true;
    });
    const sorted = [...matches];
    sorted.sort((a, b) => {
      switch (sort) {
        case 'title-desc':
          return b.title.localeCompare(a.title);
        case 'difficulty-easy':
          return (
            (DIFFICULTY_RANK[a.difficulty] ?? 99) - (DIFFICULTY_RANK[b.difficulty] ?? 99) ||
            a.title.localeCompare(b.title)
          );
        case 'difficulty-hard':
          return (
            (DIFFICULTY_RANK[b.difficulty] ?? -1) - (DIFFICULTY_RANK[a.difficulty] ?? -1) ||
            a.title.localeCompare(b.title)
          );
        case 'title-asc':
        default:
          return a.title.localeCompare(b.title);
      }
    });
    return sorted;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rounds, difficulty, topic, language, query, sort, statusFilter, statusVersion]);

  const { slice, sentinelRef, hasMore } = useInfiniteList(filtered ?? [], {
    initial: 18,
    step: 18,
  });

  return (
    <div className="h-full flex flex-col min-h-0">
      <AppHeader
        eyebrow="Track 04 · AI Assisted Coding"
        title="AI Assisted Coding"
        description="Multi-file rounds you tackle alongside an AI pair. Fix bugs, add features, optimize hot paths — graded on deterministic tests plus a rubric review of how you used the assistant."
        chromeActions={
          <PracticeStatusFilter value={statusFilter} onChange={setStatusFilter} />
        }
        compactActions={
          <PracticeStatusFilter value={statusFilter} onChange={setStatusFilter} compact />
        }
      />

      <div
        className="flex-shrink-0 px-5 sm:px-8 pt-6 pb-2"
        style={{ background: 'var(--bg)' }}
      >
        <div className="flex flex-wrap gap-2 items-center">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search title, topic, company…"
            className="mono"
            style={{
              flex: '1 1 260px',
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
          <div className="flex gap-1.5">
            {([null, 'easy', 'medium', 'hard'] as const).map((d) => (
              <button
                key={String(d)}
                type="button"
                onClick={() => setDifficulty(d)}
                style={{
                  padding: '7px 13px',
                  border: 0,
                  borderRadius: 999,
                  background: difficulty === d ? 'var(--ink)' : 'transparent',
                  color: difficulty === d ? 'var(--paper)' : 'var(--text-3)',
                  boxShadow:
                    difficulty === d ? 'none' : 'inset 0 0 0 1px var(--border-strong)',
                  fontSize: 11.5,
                  fontWeight: 500,
                  cursor: 'pointer',
                  textTransform: 'capitalize',
                }}
              >
                {d ?? 'All'}
              </button>
            ))}
          </div>
          {allTopics.length > 0 && (
            <div style={{ minWidth: 160 }}>
              <Select
                value={topic}
                onChange={setTopic}
                options={[
                  { value: ALL_OPTION, label: 'All topics' },
                  ...allTopics.map((t) => ({ value: t, label: t })),
                ]}
                ariaLabel="Topic"
              />
            </div>
          )}
          {allLanguages.length > 1 && (
            <div style={{ minWidth: 140 }}>
              <Select
                value={language}
                onChange={setLanguage}
                options={[
                  { value: ALL_OPTION, label: 'All languages' },
                  ...allLanguages.map((l) => ({ value: l, label: l })),
                ]}
                ariaLabel="Language"
              />
            </div>
          )}
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
            {filtered?.length ?? 0} OF {rounds?.length ?? 0} ROUNDS
          </span>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-5 sm:px-8 pb-6 pt-4">
        {error && (
          <div className="card" style={{ padding: 16 }}>
            Error loading rounds: {error}
          </div>
        )}
        {!error && rounds === null && (
          <div className="text-center py-16" style={{ color: 'var(--text-3)' }}>
            Loading…
          </div>
        )}
        {!error && rounds && filtered && filtered.length === 0 && (
          <div className="text-center py-16" style={{ color: 'var(--text-4)' }}>
            No rounds match that filter.
          </div>
        )}
        {!error && rounds && filtered && filtered.length > 0 && (
          <div
            className="grid gap-5"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))' }}
          >
            {slice.map((r, i) => {
              const status = effectiveStatus('ai-coding', r.slug);
              const preview = stripMarkdown(r.description).slice(0, 220);
              return (
                <Link
                  key={r.id}
                  to={`/ai-coding/round/${r.slug}`}
                  className="card card-hover fade-up flex flex-col gap-4"
                  style={{
                    padding: 28,
                    animationDelay: `${i * 30}ms`,
                    textDecoration: 'none',
                    color: 'var(--text)',
                  }}
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <DifficultyPill level={r.difficulty} />
                    <span
                      className="pill"
                      style={{
                        background: 'transparent',
                        color: 'var(--text-3)',
                        boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                      }}
                    >
                      {r.language}
                    </span>
                    <span
                      className="pill"
                      style={{
                        background: 'var(--accent-soft)',
                        color: 'var(--accent)',
                      }}
                    >
                      {r.checkpoints.length} checkpoint{r.checkpoints.length === 1 ? '' : 's'}
                    </span>
                  </div>
                  <div
                    className="display-italic"
                    style={{ fontSize: 28, lineHeight: 1.1, fontWeight: 400 }}
                  >
                    {r.title}
                  </div>
                  {preview && (
                    <p
                      style={{
                        margin: 0,
                        fontSize: 14,
                        color: 'var(--text-3)',
                        lineHeight: 1.6,
                      }}
                      className="line-clamp-3"
                    >
                      {preview}
                    </p>
                  )}
                  {r.topics && r.topics.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {r.topics.slice(0, 5).map((t) => (
                        <span
                          key={t}
                          className="pill"
                          style={{
                            background: 'transparent',
                            color: 'var(--text-3)',
                            boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                          }}
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  <div
                    className="flex items-center gap-2 pt-3 mt-auto"
                    style={{ borderTop: '1px solid var(--border)' }}
                  >
                    <StatusDot status={status} />
                    {r.companies && r.companies.length > 0 && (
                      <span
                        className="mono ml-auto"
                        style={{
                          fontSize: 10.5,
                          color: 'var(--text-4)',
                          letterSpacing: '0.05em',
                        }}
                      >
                        {r.companies.slice(0, 3).join(' · ').toUpperCase()}
                      </span>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
        {hasMore && (
          <div
            ref={sentinelRef}
            className="text-center mono"
            style={{
              padding: '24px 0',
              fontSize: 10.5,
              color: 'var(--text-4)',
              letterSpacing: '0.1em',
            }}
          >
            LOADING MORE…
          </div>
        )}
      </div>
    </div>
  );
}
