import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowRight, Check, X } from 'lucide-react';
import { api } from '../api/client';
import { AnimatedCard } from '../components/visual/AnimatedCard';
import { Skeleton } from '../components/visual/Skeleton';
import { MyAnecdotesPanel } from './behavioral/MyAnecdotesPanel';
import type { BehavioralQuestionLite } from './behavioral/types';
import PracticeStatusControl from '../components/shell/PracticeStatusControl';
import BackLink from '../components/shell/BackLink';
import SectionNav, { type SectionNavItem } from '../components/shell/SectionNav';
import { usePracticeStatus } from '../hooks/usePracticeStatus';

interface BC {
  id: number;
  name: string;
  description: string;
  color: string;
  icon: string;
}

interface BQ {
  id: number;
  title: string;
  question_text: string;
  category_ids: number[];
  star_guide: {
    situation: string;
    task: string;
    action: string;
    result: string;
    framework_tips?: string[];
  };
  sample_response: {
    situation: string;
    task: string;
    action: string;
    result: string;
    key_strengths_shown?: string[];
  };
  tips: string[];
  common_pitfalls: string[];
  follow_up_questions: string[];
  what_interviewers_look_for: string[];
  tags: string[];
}

const starLetterColor: Record<string, string> = {
  situation: 'var(--forest)',
  task: 'var(--ochre)',
  action: 'var(--accent)',
  result: 'var(--plum)',
};

function SectionHeading({ children, id }: { children: React.ReactNode; id?: string }) {
  return (
    <h2
      id={id}
      className="display-italic"
      style={{
        fontSize: 30,
        fontWeight: 400,
        lineHeight: 1.1,
        margin: '0 0 16px',
        scrollMarginTop: 24,
      }}
    >
      {children}
    </h2>
  );
}

function StatusBar({ questionId }: { questionId: number }) {
  const [status, setStatus] = usePracticeStatus('behavioral', questionId, 'todo');
  return <PracticeStatusControl status={status} onChange={setStatus} />;
}

export default function BehavioralDetail() {
  const { slug } = useParams<{ slug: string }>();
  const [q, setQ] = useState<BQ | null>(null);
  const [categories, setCategories] = useState<BC[]>([]);
  const [allQuestions, setAllQuestions] = useState<BehavioralQuestionLite[]>([]);
  const [loading, setLoading] = useState(true);

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!slug) return;
    Promise.all([
      api.get<BQ>(`/api/behavioral/${slug}`),
      api.get<BC[]>('/api/behavioral-categories'),
      api.get<{ id: number; title: string }[]>('/api/behavioral'),
    ])
      .then(([question, cats, allQ]) => {
        setQ(question);
        setCategories(cats);
        setAllQuestions(allQ.map((x) => ({ id: x.id, title: x.title })));
      })
      .finally(() => setLoading(false));
  }, [slug]);

  const sectionItems = useMemo<SectionNavItem[]>(() => {
    if (!q) return [];
    const items: SectionNavItem[] = [];
    items.push({ id: 'prompt', label: 'Prompt' });
    const hasStar =
      !!(q.star_guide.situation || q.star_guide.task || q.star_guide.action || q.star_guide.result);
    if (hasStar) items.push({ id: 'star-guide', label: 'STAR guide' });
    const hasSample =
      !!(
        q.sample_response.situation ||
        q.sample_response.task ||
        q.sample_response.action ||
        q.sample_response.result
      );
    if (hasSample) items.push({ id: 'sample-response', label: 'Sample response' });
    items.push({ id: 'anecdotes', label: 'Your anecdotes' });
    return items;
  }, [q]);

  if (loading) {
    return (
      <div className="h-full p-6 space-y-3">
        <Skeleton width={220} height={20} />
        <Skeleton width={'100%'} height={14} />
        <Skeleton width={'80%'} height={14} />
      </div>
    );
  }

  if (!q) {
    return (
      <div className="flex items-center justify-center h-full">
        <div style={{ fontSize: 13, color: 'var(--text-3)' }}>
          Question not found.{' '}
          <Link to="/behavioral" style={{ color: 'var(--accent)' }}>
            Go back
          </Link>
        </div>
      </div>
    );
  }

  const getCat = (cid: number) => categories.find((c) => c.id === cid);
  const hasStar =
    !!(q.star_guide.situation || q.star_guide.task || q.star_guide.action || q.star_guide.result);
  const hasSample =
    !!(
      q.sample_response.situation ||
      q.sample_response.task ||
      q.sample_response.action ||
      q.sample_response.result
    );

  return (
    <div className="h-full flex flex-col">
      <div className="px-8 pt-5 pb-4" style={{ borderBottom: '1px solid var(--border)' }}>
        <BackLink to="/behavioral" label="All questions" />
        <div className="flex gap-2 mt-3 flex-wrap">
          {q.category_ids.map((cid) => {
            const c = getCat(cid);
            if (!c) return null;
            return (
              <span
                key={cid}
                className="pill"
                style={{
                  background: 'transparent',
                  color: c.color,
                  boxShadow: `inset 0 0 0 1px ${c.color}`,
                }}
              >
                {c.name}
              </span>
            );
          })}
        </div>
        <div className="flex items-end justify-between gap-5 mt-3 flex-wrap">
          <div className="min-w-0" style={{ flex: '1 1 520px' }}>
            <h1
              className="display-italic"
              style={{
                margin: 0,
                fontSize: 38,
                lineHeight: 1.05,
                fontWeight: 400,
                maxWidth: 780,
              }}
            >
              {q.title}
            </h1>
            <p
              style={{
                margin: '12px 0 0',
                color: 'var(--text-2)',
                fontSize: 15,
                maxWidth: 780,
                lineHeight: 1.6,
              }}
            >
              {q.question_text}
            </p>
          </div>
          <div style={{ paddingBottom: 6 }}>
            <div className="eyebrow mb-2">Your status</div>
            <StatusBar questionId={q.id} />
          </div>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto">
        <div
          className="px-8 py-8 grid gap-10"
          style={{ gridTemplateColumns: 'minmax(0, 1fr) 300px' }}
        >
          <main className="space-y-12 min-w-0">
            <section>
              <SectionHeading id="prompt">Prompt</SectionHeading>
              <AnimatedCard className="card" style={{ padding: 28 }}>
                <div className="eyebrow mb-3">The question</div>
                <p
                  className="display"
                  style={{ margin: 0, fontSize: 22, fontWeight: 400, lineHeight: 1.45 }}
                >
                  "{q.question_text}"
                </p>
              </AnimatedCard>
            </section>

            {hasStar && (
              <section>
                <SectionHeading id="star-guide">STAR guide</SectionHeading>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {(
                    [
                      [
                        'situation',
                        'Set the scene. Enough context so we know why this matters, not a biography.',
                      ],
                      [
                        'task',
                        'Your specific responsibility. Make your role unmistakable.',
                      ],
                      [
                        'action',
                        'What you did, concretely. Use "I" not "we" for your contributions.',
                      ],
                      [
                        'result',
                        "Outcome with a number. If you don't have one, say so and say what changed.",
                      ],
                    ] as const
                  ).map(([key, blurb], i) => (
                    <AnimatedCard
                      key={key}
                      className="card"
                      style={{ padding: 22 }}
                      delay={i * 0.04}
                    >
                      <div className="flex items-baseline gap-3 mb-2.5">
                        <span
                          className="display-italic"
                          style={{
                            fontSize: 40,
                            color: starLetterColor[key],
                            lineHeight: 1,
                          }}
                        >
                          {key[0].toUpperCase()}
                        </span>
                        <span
                          className="display"
                          style={{
                            fontSize: 20,
                            fontWeight: 400,
                            textTransform: 'capitalize',
                          }}
                        >
                          {key}
                        </span>
                      </div>
                      <p
                        style={{
                          margin: 0,
                          fontSize: 14,
                          color: 'var(--text-2)',
                          lineHeight: 1.6,
                        }}
                      >
                        {q.star_guide[key] || blurb}
                      </p>
                    </AnimatedCard>
                  ))}
                </div>
                {q.star_guide.framework_tips && q.star_guide.framework_tips.length > 0 && (
                  <AnimatedCard className="card mt-4" style={{ padding: 20 }}>
                    <div className="eyebrow mb-2.5">Framework tips</div>
                    <ul className="space-y-1.5">
                      {q.star_guide.framework_tips.map((tip, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-2"
                          style={{ fontSize: 13.5, color: 'var(--text-2)' }}
                        >
                          <span style={{ color: 'var(--accent)' }}>→</span>
                          <span>{tip}</span>
                        </li>
                      ))}
                    </ul>
                  </AnimatedCard>
                )}
              </section>
            )}

            {hasSample && (
              <section>
                <SectionHeading id="sample-response">Sample response</SectionHeading>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {(['situation', 'task', 'action', 'result'] as const).map((k, i) => (
                    <AnimatedCard
                      key={k}
                      className="card"
                      style={{ padding: 22 }}
                      delay={i * 0.04}
                    >
                      <div className="flex items-baseline gap-3 mb-3">
                        <span
                          className="display-italic"
                          style={{
                            fontSize: 38,
                            lineHeight: 1,
                            color: starLetterColor[k],
                            fontWeight: 400,
                          }}
                        >
                          {k[0].toUpperCase()}
                        </span>
                        <span
                          className="mono uppercase"
                          style={{
                            fontSize: 10.5,
                            letterSpacing: '0.14em',
                            color: 'var(--text-3)',
                          }}
                        >
                          {k}
                        </span>
                      </div>
                      <p
                        style={{
                          margin: 0,
                          fontSize: 14.5,
                          lineHeight: 1.65,
                          color: 'var(--text-2)',
                        }}
                      >
                        {q.sample_response[k]}
                      </p>
                    </AnimatedCard>
                  ))}
                </div>
              </section>
            )}

            <section>
              <SectionHeading id="anecdotes">Your anecdotes</SectionHeading>
              <MyAnecdotesPanel
                questionId={q.id}
                questionCategoryIds={q.category_ids}
                categories={categories}
                questions={allQuestions}
              />
            </section>
          </main>

          <aside>
            <div
              style={{
                position: 'sticky',
                top: 16,
                maxHeight: 'calc(100vh - 32px)',
                display: 'flex',
                flexDirection: 'column',
                gap: 16,
              }}
            >
              <div style={{ background: 'var(--bg)', flexShrink: 0, paddingBottom: 4 }}>
                <SectionNav items={sectionItems} scrollContainer={scrollRef} nonSticky />
              </div>
              <div
                className="space-y-5"
                style={{ overflowY: 'auto', paddingRight: 4, minHeight: 0 }}
              >

              {q.follow_up_questions.length > 0 && (
                <div className="card p-4">
                  <div className="eyebrow mb-3" style={{ color: 'var(--accent)' }}>
                    Likely follow-ups
                  </div>
                  <ul className="flex flex-col gap-2 list-none p-0 m-0">
                    {q.follow_up_questions.map((f, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2"
                        style={{ fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.5 }}
                      >
                        <span
                          className="display-italic"
                          style={{
                            color: 'var(--accent)',
                            fontSize: 16,
                            lineHeight: 1,
                            flexShrink: 0,
                          }}
                        >
                          ?
                        </span>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {(q.tips.length > 0 || q.common_pitfalls.length > 0) && (
                <div className="card p-4">
                  {q.tips.length > 0 && (
                    <>
                      <div
                        className="eyebrow mb-2 inline-flex items-center gap-1.5"
                        style={{ color: 'var(--forest)' }}
                      >
                        <Check size={11} strokeWidth={2} />
                        Do
                      </div>
                      <ul className="flex flex-col gap-1.5 list-none p-0 m-0 mb-3">
                        {q.tips.map((t, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-2"
                            style={{ fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.5 }}
                          >
                            <Check
                              size={12}
                              strokeWidth={2}
                              style={{
                                color: 'var(--forest)',
                                marginTop: 2,
                                flexShrink: 0,
                              }}
                            />
                            <span>{t}</span>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                  {q.common_pitfalls.length > 0 && (
                    <>
                      {q.tips.length > 0 && (
                        <div
                          style={{
                            borderTop: '1px solid var(--border)',
                            marginBottom: 10,
                          }}
                        />
                      )}
                      <div
                        className="eyebrow mb-2 inline-flex items-center gap-1.5"
                        style={{ color: 'var(--plum)' }}
                      >
                        <X size={11} strokeWidth={2} />
                        Don't
                      </div>
                      <ul className="flex flex-col gap-1.5 list-none p-0 m-0">
                        {q.common_pitfalls.map((p, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-2"
                            style={{ fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.5 }}
                          >
                            <X
                              size={12}
                              strokeWidth={2}
                              style={{
                                color: 'var(--plum)',
                                marginTop: 2,
                                flexShrink: 0,
                              }}
                            />
                            <span>{p}</span>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </div>
              )}

              {q.sample_response.key_strengths_shown &&
                q.sample_response.key_strengths_shown.length > 0 && (
                  <div className="card p-4">
                    <div className="eyebrow mb-3">Strengths demonstrated</div>
                    <div className="flex flex-wrap gap-1.5">
                      {q.sample_response.key_strengths_shown.map((s) => (
                        <span
                          key={s}
                          className="pill"
                          style={{
                            background: 'var(--accent-soft)',
                            color: 'var(--accent)',
                          }}
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

              {q.what_interviewers_look_for.length > 0 && (
                <div className="card p-4">
                  <div
                    className="eyebrow mb-3 inline-flex items-center gap-1.5"
                    style={{ color: 'var(--ochre)' }}
                  >
                    <ArrowRight size={11} strokeWidth={1.8} />
                    Interviewers look for
                  </div>
                  <ul className="flex flex-col gap-2 list-none p-0 m-0">
                    {q.what_interviewers_look_for.map((w, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2"
                        style={{ fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.5 }}
                      >
                        <span style={{ color: 'var(--text-4)' }}>·</span>
                        <span>{w}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
