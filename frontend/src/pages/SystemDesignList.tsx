import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { listSystemDesignQuestions } from '../content/api';
import { slugify } from '../lib/slug';
import AppHeader from '../components/shell/AppHeader';
import DifficultyPill from '../components/shell/DifficultyPill';
import StatusDot from '../components/shell/StatusDot';
import Select from '../components/shell/Select';
import { effectiveStatus, useStatusMapVersion } from '../hooks/usePracticeStatus';
import { useInfiniteList } from '../hooks/useInfiniteList';
import { usePersistedState } from '../hooks/usePersistedState';
import PracticeStatusFilter, {
  type PracticeStatusFilterValue,
} from '../components/shell/PracticeStatusFilter';

type SortKey =
  | 'title-asc'
  | 'title-desc'
  | 'difficulty-easy'
  | 'difficulty-hard'
  | 'recent'
  | 'oldest';

const DIFFICULTY_RANK: Record<string, number> = { Easy: 0, Medium: 1, Hard: 2 };

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'title-asc', label: 'Title (A–Z)' },
  { value: 'title-desc', label: 'Title (Z–A)' },
  { value: 'difficulty-easy', label: 'Difficulty (Easy first)' },
  { value: 'difficulty-hard', label: 'Difficulty (Hard first)' },
  { value: 'recent', label: 'Recently updated' },
  { value: 'oldest', label: 'Oldest first' },
];

const ALL_OPTION = '__all__';

interface SDQ {
  id: number;
  title: string;
  difficulty: string;
  description: string;
  tags: string[];
  updated_at?: string | null;
}

export default function SystemDesignList() {
  const [questions, setQuestions] = useState<SDQ[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [difficulty, setDifficulty] = usePersistedState<string | null>('rounds.sd.difficulty', null);
  const [tag, setTag] = usePersistedState<string>('rounds.sd.tag', ALL_OPTION);
  const [sort, setSort] = usePersistedState<SortKey>('rounds.sd.sort', 'title-asc');
  const [statusFilter, setStatusFilter] = usePersistedState<PracticeStatusFilterValue>(
    'rounds.sd.statusFilter',
    'all',
  );
  const statusVersion = useStatusMapVersion();

  useEffect(() => {
    listSystemDesignQuestions<SDQ>()
      .then(setQuestions)
      .finally(() => setLoading(false));
  }, []);

  const allTags = useMemo(() => {
    const set = new Set<string>();
    for (const q of questions) for (const t of q.tags ?? []) set.add(t);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [questions]);

  const filtered = useMemo(() => {
    const matches = questions.filter((q) => {
      if (difficulty && q.difficulty !== difficulty) return false;
      if (tag !== ALL_OPTION && !(q.tags ?? []).includes(tag)) return false;
      if (statusFilter !== 'all' && effectiveStatus('system', q.id) !== statusFilter) return false;
      if (query.trim()) {
        const s = query.trim().toLowerCase();
        const blob = `${q.title} ${(q.tags ?? []).join(' ')} ${q.description ?? ''}`.toLowerCase();
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
          return (DIFFICULTY_RANK[a.difficulty] ?? 99) - (DIFFICULTY_RANK[b.difficulty] ?? 99) ||
            a.title.localeCompare(b.title);
        case 'difficulty-hard':
          return (DIFFICULTY_RANK[b.difficulty] ?? -1) - (DIFFICULTY_RANK[a.difficulty] ?? -1) ||
            a.title.localeCompare(b.title);
        case 'recent':
          return (b.updated_at ?? '').localeCompare(a.updated_at ?? '') ||
            a.title.localeCompare(b.title);
        case 'oldest':
          return (a.updated_at ?? '￿').localeCompare(b.updated_at ?? '￿') ||
            a.title.localeCompare(b.title);
        case 'title-asc':
        default:
          return a.title.localeCompare(b.title);
      }
    });
    return sorted;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questions, difficulty, tag, query, sort, statusFilter, statusVersion]);

  const { slice, sentinelRef, hasMore } = useInfiniteList(filtered, { initial: 18, step: 18 });

  return (
    <div className="h-full flex flex-col min-h-0">
      <AppHeader
        eyebrow="Track 01 · System Design"
        title="System Design"
        description="Designing at scale is practice, not talent. Walk the same ground until the tradeoffs come naturally."
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
            placeholder="Search title, tag, summary…"
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
            {([null, 'Easy', 'Medium', 'Hard'] as const).map((d) => (
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
                }}
              >
                {d ?? 'All'}
              </button>
            ))}
          </div>
          {allTags.length > 0 && (
            <div style={{ minWidth: 160 }}>
              <Select
                value={tag}
                onChange={setTag}
                options={[
                  { value: ALL_OPTION, label: 'All tags' },
                  ...allTags.map((t) => ({ value: t, label: t })),
                ]}
                ariaLabel="Tag"
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
            {filtered.length} OF {questions.length} DESIGNS
          </span>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-5 sm:px-8 pb-6 pt-4">
        {loading ? (
          <div className="text-center py-16" style={{ color: 'var(--text-3)' }}>
            Loading…
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16" style={{ color: 'var(--text-4)' }}>
            No designs match that filter.
          </div>
        ) : (
          <div
            className="grid gap-5"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))' }}
          >
            {slice.map((q, i) => {
              const status = effectiveStatus('system', q.id);
              return (
                <Link
                  key={q.id}
                  to={`/system-design/question/${slugify(q.title) || q.id}`}
                  className="card card-hover fade-up flex flex-col gap-4"
                  style={{
                    padding: 28,
                    animationDelay: `${i * 30}ms`,
                    textDecoration: 'none',
                    color: 'var(--text)',
                  }}
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <DifficultyPill level={q.difficulty} />
                  </div>
                  <div
                    className="display-italic"
                    style={{ fontSize: 30, lineHeight: 1.1, fontWeight: 400 }}
                  >
                    {q.title}
                  </div>
                  <p
                    style={{
                      margin: 0,
                      fontSize: 14,
                      color: 'var(--text-3)',
                      lineHeight: 1.6,
                    }}
                    className="line-clamp-3"
                  >
                    {q.description}
                  </p>
                  {q.tags && q.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {q.tags.slice(0, 5).map((tag) => (
                        <span
                          key={tag}
                          className="pill"
                          style={{
                            background: 'transparent',
                            color: 'var(--text-3)',
                            boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                          }}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <div
                    className="flex items-center gap-2 pt-3 mt-auto"
                    style={{ borderTop: '1px solid var(--border)' }}
                  >
                    <StatusDot status={status} />
                    {q.updated_at && (
                      <span
                        className="mono ml-auto"
                        style={{ fontSize: 10.5, color: 'var(--text-4)' }}
                      >
                        {new Date(q.updated_at).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                        })}
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
