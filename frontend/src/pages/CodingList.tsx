import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { slugify } from '../lib/slug';
import AppHeader from '../components/shell/AppHeader';
import DifficultyPill from '../components/shell/DifficultyPill';
import StatusDot from '../components/shell/StatusDot';
import Select from '../components/shell/Select';
import { effectiveStatus } from '../hooks/usePracticeStatus';
import { useInfiniteList } from '../hooks/useInfiniteList';
import { usePersistedState } from '../hooks/usePersistedState';

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

interface CQ {
  id: number;
  title: string;
  difficulty: string;
  description: string;
  topics: string[];
  companies: string[];
  time_complexity: string;
  space_complexity: string;
  updated_at?: string | null;
}

// Strip markdown / backticks / collapse whitespace for a preview line.
function previewLine(raw: string): string {
  return raw
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

export default function CodingList() {
  const [questions, setQuestions] = useState<CQ[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [difficulty, setDifficulty] = usePersistedState<string | null>('rounds.coding.difficulty', null);
  const [topic, setTopic] = usePersistedState<string>('rounds.coding.topic', ALL_OPTION);
  const [company, setCompany] = usePersistedState<string>('rounds.coding.company', ALL_OPTION);
  const [sort, setSort] = usePersistedState<SortKey>('rounds.coding.sort', 'title-asc');

  useEffect(() => {
    api
      .get<CQ[]>('/api/coding')
      .then(setQuestions)
      .finally(() => setLoading(false));
  }, []);

  // Aggregated facets — derived from the loaded list so filter dropdowns
  // only ever offer real values. Sorted alphabetically; long lists are
  // expected (e.g. 30+ topics) so the dropdown handles its own scroll.
  const allTopics = useMemo(() => {
    const set = new Set<string>();
    for (const q of questions) for (const t of q.topics ?? []) set.add(t);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [questions]);
  const allCompanies = useMemo(() => {
    const set = new Set<string>();
    for (const q of questions) for (const c of q.companies ?? []) set.add(c);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [questions]);

  const filtered = useMemo(() => {
    const matches = questions.filter((q) => {
      if (difficulty && q.difficulty !== difficulty) return false;
      if (topic !== ALL_OPTION && !(q.topics ?? []).includes(topic)) return false;
      if (company !== ALL_OPTION && !(q.companies ?? []).includes(company)) return false;
      if (query.trim()) {
        const s = query.trim().toLowerCase();
        const blob = `${q.title} ${q.topics.join(' ')} ${q.companies.join(' ')}`.toLowerCase();
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
          // Items without an updated_at sink to the bottom.
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
  }, [questions, difficulty, topic, company, query, sort]);

  const { slice, sentinelRef, hasMore } = useInfiniteList(filtered, { initial: 30, step: 30 });

  return (
    <div className="h-full flex flex-col min-h-0">
      <AppHeader
        eyebrow="Track 02 · Coding"
        title="Coding"
        description="Algorithms and data structures, one problem at a time. Start with the pattern, then sharpen the implementation."
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
          {allCompanies.length > 0 && (
            <div style={{ minWidth: 160 }}>
              <Select
                value={company}
                onChange={setCompany}
                options={[
                  { value: ALL_OPTION, label: 'All companies' },
                  ...allCompanies.map((c) => ({ value: c, label: c })),
                ]}
                ariaLabel="Company"
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
            {filtered.length} OF {questions.length} PROBLEMS
          </span>
        </div>
      </div>

      <div className="flex-shrink-0 px-5 sm:px-8 pt-4">
        <div
          className="eyebrow hidden md:grid items-center gap-3"
          style={{
            gridTemplateColumns:
              '64px minmax(0, 2.8fr) 110px minmax(0, 1.3fr) minmax(0, 1.1fr) 130px',
            padding: '12px 20px',
            border: '1px solid var(--border)',
            borderBottom: 0,
            borderTopLeftRadius: 'var(--radius)',
            borderTopRightRadius: 'var(--radius)',
            background: 'var(--bg-sunken)',
            fontSize: 9.5,
          }}
        >
          <span>#</span>
          <span>Problem</span>
          <span>Difficulty</span>
          <span>Topics</span>
          <span>Companies</span>
          <span style={{ textAlign: 'right' }}>Complexity</span>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-5 sm:px-8 pb-6">
        <div
          className="card"
          style={{
            overflow: 'hidden',
            borderTopLeftRadius: 0,
            borderTopRightRadius: 0,
          }}
        >
          {loading ? (
            <div className="p-12 text-center" style={{ color: 'var(--text-3)' }}>
              Loading…
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-12 text-center" style={{ color: 'var(--text-4)' }}>
              No problems match that filter.
            </div>
          ) : (
            <>
              {slice.map((q, i) => (
                <CodingRow
                  key={q.id}
                  q={q}
                  last={!hasMore && i === slice.length - 1}
                  index={i}
                />
              ))}
              {hasMore && (
                <div
                  ref={sentinelRef}
                  className="p-6 text-center mono"
                  style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}
                >
                  LOADING MORE…
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function CodingRow({ q, last, index }: { q: CQ; last: boolean; index: number }) {
  const status = effectiveStatus('coding', q.id);
  const preview = previewLine(q.description);
  return (
    <Link
      to={`/coding/question/${slugify(q.title) || q.id}`}
      className="fade-up transition-colors block md:grid md:gap-3"
      style={{
        gridTemplateColumns:
          '64px minmax(0, 2.8fr) 110px minmax(0, 1.3fr) minmax(0, 1.1fr) 130px',
        padding: '14px 20px',
        borderBottom: last ? 'none' : '1px solid var(--border)',
        textDecoration: 'none',
        color: 'var(--text)',
        animationDelay: `${Math.min(index, 12) * 18}ms`,
        alignItems: 'flex-start',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'var(--bg-sunken)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'transparent';
      }}
    >
      {/* Row 1 on mobile / first column on desktop */}
      <div className="flex items-center gap-2 md:block">
        <span
          className="mono"
          style={{
            fontSize: 11,
            color: 'var(--text-4)',
            letterSpacing: '0.04em',
          }}
        >
          #{String(index + 1).padStart(3, '0')}
        </span>
        <span className="md:hidden ml-auto">
          <DifficultyPill level={q.difficulty} />
        </span>
      </div>

      <div className="min-w-0 mt-1.5 md:mt-0">
        <div
          className="display-italic"
          style={{ fontSize: 18, fontWeight: 400, lineHeight: 1.2 }}
        >
          {q.title}
        </div>
        <p
          className="line-clamp-2 md:line-clamp-3"
          style={{
            margin: '4px 0 0',
            fontSize: 12.5,
            color: 'var(--text-3)',
            lineHeight: 1.55,
          }}
        >
          {preview}
        </p>
        <div
          className="flex items-center gap-2 mt-2 md:hidden flex-wrap"
          style={{ fontSize: 11, color: 'var(--text-4)' }}
        >
          <StatusDot status={status} />
          {q.topics.slice(0, 2).map((t) => (
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
          {q.topics.length > 2 && (
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
              +{q.topics.length - 2}
            </span>
          )}
          <span
            className="mono ml-auto"
            style={{ fontSize: 10, color: 'var(--text-4)' }}
          >
            {q.time_complexity || '—'} · {q.space_complexity || '—'}
          </span>
        </div>
        <div
          className="hidden md:flex items-center gap-2 mt-2"
          style={{ fontSize: 11, color: 'var(--text-4)' }}
        >
          <StatusDot status={status} />
        </div>
      </div>

      {/* Desktop-only columns — hidden on mobile (info folded into row above) */}
      <div className="hidden md:block">
        <DifficultyPill level={q.difficulty} />
      </div>
      <div className="hidden md:flex flex-wrap gap-1 min-w-0">
        {q.topics.slice(0, 2).map((t) => (
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
        {q.topics.length > 2 && (
          <span
            className="mono"
            style={{ fontSize: 10.5, color: 'var(--text-4)', alignSelf: 'center' }}
          >
            +{q.topics.length - 2}
          </span>
        )}
      </div>
      <div className="hidden md:flex flex-wrap gap-1 min-w-0">
        {q.companies.slice(0, 2).map((c) => (
          <span
            key={c}
            className="pill"
            style={{
              background: 'var(--bg-sunken)',
              color: 'var(--text-3)',
              fontSize: 10,
            }}
          >
            {c}
          </span>
        ))}
        {q.companies.length > 2 && (
          <span
            className="mono"
            style={{ fontSize: 10.5, color: 'var(--text-4)', alignSelf: 'center' }}
          >
            +{q.companies.length - 2}
          </span>
        )}
      </div>
      <span
        className="mono hidden md:block"
        style={{ fontSize: 10.5, color: 'var(--text-4)', textAlign: 'right' }}
      >
        {q.time_complexity || '—'} · {q.space_complexity || '—'}
      </span>
    </Link>
  );
}
