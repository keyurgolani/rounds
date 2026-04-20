import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { slugify } from '../lib/slug';
import PageHeader from '../components/shell/PageHeader';
import DifficultyPill from '../components/shell/DifficultyPill';
import StatusDot from '../components/shell/StatusDot';
import { effectiveStatus } from '../hooks/usePracticeStatus';

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

  useEffect(() => {
    api
      .get<SDQ[]>('/api/system-design')
      .then(setQuestions)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        eyebrow="Track 01 · System Design"
        title="System Design"
        subtitle="Designing at scale is practice, not talent. Walk the same ground until the tradeoffs come naturally."
      />

      <div className="mx-auto px-8 py-6" style={{ maxWidth: 1280 }}>
        {loading ? (
          <div className="text-center py-16" style={{ color: 'var(--text-3)' }}>
            Loading…
          </div>
        ) : (
          <div
            className="grid gap-4"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}
          >
            {questions.map((q, i) => {
              const status = effectiveStatus('system', q.id);
              return (
                <Link
                  key={q.id}
                  to={`/system-design/question/${slugify(q.title) || q.id}`}
                  className="card card-hover fade-up flex flex-col gap-3"
                  style={{
                    padding: 20,
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
                    style={{ fontSize: 24, lineHeight: 1.15, fontWeight: 400 }}
                  >
                    {q.title}
                  </div>
                  <p
                    style={{
                      margin: 0,
                      fontSize: 12.5,
                      color: 'var(--text-3)',
                      lineHeight: 1.55,
                    }}
                    className="line-clamp-3"
                  >
                    {q.description}
                  </p>
                  {q.tags && q.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {q.tags.slice(0, 4).map((tag) => (
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
                    className="flex items-center gap-2 pt-2"
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
      </div>
    </div>
  );
}
