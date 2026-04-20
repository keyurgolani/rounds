import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { slugify } from '../lib/slug';
import PageHeader from '../components/shell/PageHeader';
import DifficultyPill from '../components/shell/DifficultyPill';
import StatusDot from '../components/shell/StatusDot';
import { effectiveStatus } from '../hooks/usePracticeStatus';

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
  const [difficulty, setDifficulty] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<CQ[]>('/api/coding')
      .then(setQuestions)
      .finally(() => setLoading(false));
  }, []);

  const filtered = questions.filter((q) => {
    if (difficulty && q.difficulty !== difficulty) return false;
    if (query.trim()) {
      const s = query.trim().toLowerCase();
      const blob = `${q.title} ${q.topics.join(' ')} ${q.companies.join(' ')}`.toLowerCase();
      if (!blob.includes(s)) return false;
    }
    return true;
  });

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        eyebrow="Track 02 · Coding"
        title="Coding"
        subtitle="Algorithms and data structures, one problem at a time. Start with the pattern, then sharpen the implementation."
      />

      <div className="mx-auto px-8 py-6" style={{ maxWidth: 1280 }}>
        <div className="flex flex-wrap gap-2 mb-5 items-center">
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
          <span
            className="mono ml-auto"
            style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}
          >
            {filtered.length} OF {questions.length} PROBLEMS
          </span>
        </div>

        <div className="card overflow-hidden">
          <div
            className="eyebrow grid items-center gap-3"
            style={{
              gridTemplateColumns:
                '56px minmax(0, 2.8fr) 110px minmax(0, 1.3fr) minmax(0, 1.1fr) 130px',
              padding: '12px 20px',
              borderBottom: '1px solid var(--border)',
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

          {loading ? (
            <div className="p-12 text-center" style={{ color: 'var(--text-3)' }}>
              Loading…
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-12 text-center" style={{ color: 'var(--text-4)' }}>
              No problems match that filter.
            </div>
          ) : (
            filtered.map((q, i) => (
              <CodingRow key={q.id} q={q} last={i === filtered.length - 1} index={i} />
            ))
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
      className="fade-up grid gap-3 transition-colors"
      style={{
        gridTemplateColumns:
          '56px minmax(0, 2.8fr) 110px minmax(0, 1.3fr) minmax(0, 1.1fr) 130px',
        padding: '16px 20px',
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
      <span
        className="mono"
        style={{
          fontSize: 11,
          color: 'var(--text-4)',
          letterSpacing: '0.04em',
          paddingTop: 4,
        }}
      >
        #{String(q.id).padStart(3, '0')}
      </span>
      <div className="min-w-0">
        <div
          className="display-italic"
          style={{ fontSize: 18, fontWeight: 400, lineHeight: 1.2 }}
        >
          {q.title}
        </div>
        <p
          className="line-clamp-3"
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
          className="flex items-center gap-2 mt-2"
          style={{ fontSize: 11, color: 'var(--text-4)' }}
        >
          <StatusDot status={status} />
        </div>
      </div>
      <DifficultyPill level={q.difficulty} />
      <div className="flex flex-wrap gap-1 min-w-0">
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
      <div className="flex flex-wrap gap-1 min-w-0">
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
        className="mono"
        style={{ fontSize: 10.5, color: 'var(--text-4)', textAlign: 'right' }}
      >
        {q.time_complexity || '—'} · {q.space_complexity || '—'}
      </span>
    </Link>
  );
}
