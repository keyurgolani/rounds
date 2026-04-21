import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Check, X } from 'lucide-react';
import { api } from '../api/client';
import { AnimatedCard } from '../components/visual/AnimatedCard';
import { PageTransition } from '../components/visual/PageTransition';
import { Skeleton } from '../components/visual/Skeleton';
import { MyAnecdotesPanel } from './behavioral/MyAnecdotesPanel';
import type { BehavioralQuestionLite } from './behavioral/types';
import Tabs from '../components/shell/Tabs';
import PracticeStatusControl from '../components/shell/PracticeStatusControl';
import BackLink from '../components/shell/BackLink';
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

const tabs = [
  { key: 'question', label: 'Question & Anecdotes' },
  { key: 'star', label: 'STAR Guide & Tips' },
  { key: 'sample', label: 'Sample Response' },
];

const starLetterColor: Record<string, string> = {
  situation: 'var(--forest)',
  task: 'var(--ochre)',
  action: 'var(--accent)',
  result: 'var(--plum)',
};

export default function BehavioralDetail() {
  const { slug } = useParams<{ slug: string }>();
  const [q, setQ] = useState<BQ | null>(null);
  const [categories, setCategories] = useState<BC[]>([]);
  const [allQuestions, setAllQuestions] = useState<BehavioralQuestionLite[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('question');
  const [status, setStatus] = usePracticeStatus('behavioral', slug ?? '', 'todo');

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

  return (
    <div className="h-full flex flex-col">
      <div className="px-8 pt-5 pb-4">
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
            <PracticeStatusControl status={status} onChange={setStatus} />
          </div>
        </div>
      </div>

      <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} />

      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="px-8 py-6 w-full">
          <PageTransition routeKey={activeTab}>
            {activeTab === 'question' && (
              <div>
                {/* Question block */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                  <AnimatedCard className="lg:col-span-7 card" style={{ padding: 28 }}>
                    <div className="eyebrow mb-3">The prompt</div>
                    <p
                      className="display"
                      style={{ margin: 0, fontSize: 22, fontWeight: 400, lineHeight: 1.4 }}
                    >
                      "{q.question_text}"
                    </p>
                  </AnimatedCard>
                  {q.follow_up_questions.length > 0 && (
                    <AnimatedCard className="lg:col-span-5 card" style={{ padding: 20 }} delay={0.05}>
                      <div className="eyebrow mb-3">Likely follow-ups</div>
                      {q.follow_up_questions.map((f, i) => (
                        <div
                          key={i}
                          className="flex gap-2.5 py-2"
                          style={{
                            borderBottom:
                              i < q.follow_up_questions.length - 1 ? '1px solid var(--border)' : 'none',
                          }}
                        >
                          <span
                            className="display-italic"
                            style={{ fontSize: 18, color: 'var(--accent)', lineHeight: 1 }}
                          >
                            ?
                          </span>
                          <span style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.5 }}>
                            {f}
                          </span>
                        </div>
                      ))}
                    </AnimatedCard>
                  )}
                </div>

                {/* Anecdotes block */}
                <div style={{ margin: '32px 0 16px' }}>
                  <div className="eyebrow">Your anecdotes</div>
                </div>
                <MyAnecdotesPanel
                  questionId={q.id}
                  questionCategoryIds={q.category_ids}
                  categories={categories}
                  questions={allQuestions}
                />
              </div>
            )}

            {activeTab === 'star' && (
              <div>
                {/* STAR Guide block */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  {(
                    [
                      ['situation', 'Set the scene. Enough context so we know why this matters, not a biography.'],
                      ['task', 'Your specific responsibility. Make your role unmistakable.'],
                      ['action', 'What you did, concretely. Use "I" not "we" for your contributions.'],
                      ['result', "Outcome with a number. If you don't have one, say so and say what changed."],
                    ] as const
                  ).map(([key, blurb], i) => (
                    <AnimatedCard key={key} className="card" style={{ padding: 22 }} delay={i * 0.04}>
                      <div className="flex items-baseline gap-3 mb-2.5">
                        <span
                          className="display-italic"
                          style={{ fontSize: 38, color: starLetterColor[key], lineHeight: 1 }}
                        >
                          {key[0].toUpperCase()}
                        </span>
                        <span className="display" style={{ fontSize: 20, fontWeight: 400, textTransform: 'capitalize' }}>
                          {key}
                        </span>
                      </div>
                      <p style={{ margin: 0, fontSize: 13.5, color: 'var(--text-2)', lineHeight: 1.6 }}>
                        {q.star_guide[key] || blurb}
                      </p>
                    </AnimatedCard>
                  ))}
                  {q.star_guide.framework_tips && q.star_guide.framework_tips.length > 0 && (
                    <AnimatedCard className="card md:col-span-2" style={{ padding: 20 }}>
                      <div className="eyebrow mb-2.5">Framework tips</div>
                      <ul className="space-y-1.5">
                        {q.star_guide.framework_tips.map((tip, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-2"
                            style={{ fontSize: 13, color: 'var(--text-2)' }}
                          >
                            <span style={{ color: 'var(--accent)' }}>→</span>
                            <span>{tip}</span>
                          </li>
                        ))}
                      </ul>
                    </AnimatedCard>
                  )}
                </div>

                {/* Tips & Pitfalls block */}
                <div style={{ margin: '32px 0 16px' }}>
                  <div className="eyebrow">Tips & Pitfalls</div>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                  {q.tips.length > 0 && (
                    <AnimatedCard className="card" style={{ padding: 22 }}>
                      <div className="eyebrow mb-3" style={{ color: 'var(--forest)' }}>
                        Do
                      </div>
                      {q.tips.map((t, i) => (
                        <div
                          key={i}
                          className="flex gap-2.5 py-2"
                          style={{
                            borderBottom:
                              i < q.tips.length - 1 ? '1px solid var(--border)' : 'none',
                          }}
                        >
                          <Check size={14} strokeWidth={2} style={{ color: 'var(--forest)', flexShrink: 0, marginTop: 2 }} />
                          <span style={{ fontSize: 13.5, color: 'var(--text-2)', lineHeight: 1.5 }}>
                            {t}
                          </span>
                        </div>
                      ))}
                    </AnimatedCard>
                  )}
                  {q.common_pitfalls.length > 0 && (
                    <AnimatedCard className="card" style={{ padding: 22 }} delay={0.05}>
                      <div className="eyebrow mb-3" style={{ color: 'var(--plum)' }}>
                        Don't
                      </div>
                      {q.common_pitfalls.map((p, i) => (
                        <div
                          key={i}
                          className="flex gap-2.5 py-2"
                          style={{
                            borderBottom:
                              i < q.common_pitfalls.length - 1 ? '1px solid var(--border)' : 'none',
                          }}
                        >
                          <X size={14} strokeWidth={2} style={{ color: 'var(--plum)', flexShrink: 0, marginTop: 2 }} />
                          <span style={{ fontSize: 13.5, color: 'var(--text-2)', lineHeight: 1.5 }}>
                            {p}
                          </span>
                        </div>
                      ))}
                    </AnimatedCard>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'sample' && (
              <div className="space-y-5" style={{ maxWidth: 900 }}>
                <AnimatedCard className="card" style={{ padding: 24 }}>
                  <div className="eyebrow mb-2">Sample response</div>
                  <p
                    className="display-italic"
                    style={{
                      margin: 0,
                      fontSize: 20,
                      lineHeight: 1.45,
                      fontWeight: 400,
                      color: 'var(--text-2)',
                    }}
                  >
                    {q.question_text ? `"${q.question_text}"` : 'A worked example of a strong STAR answer.'}
                  </p>
                </AnimatedCard>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                  {(['situation', 'task', 'action', 'result'] as const).map((k, i) => (
                    <AnimatedCard key={k} className="card" style={{ padding: 22 }} delay={i * 0.04}>
                      <div className="flex items-baseline gap-3 mb-3">
                        <span
                          className="display-italic"
                          style={{
                            fontSize: 36,
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

                {q.sample_response.key_strengths_shown &&
                  q.sample_response.key_strengths_shown.length > 0 && (
                    <AnimatedCard className="card" style={{ padding: 22 }}>
                      <div className="eyebrow mb-3">Key strengths demonstrated</div>
                      <div className="flex flex-wrap gap-1.5">
                        {q.sample_response.key_strengths_shown.map((s) => (
                          <span
                            key={s}
                            className="pill"
                            style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    </AnimatedCard>
                  )}

                {q.what_interviewers_look_for &&
                  q.what_interviewers_look_for.length > 0 && (
                    <AnimatedCard className="card" style={{ padding: 22 }}>
                      <div className="eyebrow mb-3">What interviewers look for</div>
                      <ul className="flex flex-col gap-2">
                        {q.what_interviewers_look_for.map((w, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-2"
                            style={{ fontSize: 13.5, color: 'var(--text-2)' }}
                          >
                            <span style={{ color: 'var(--text-4)' }}>•</span>
                            <span>{w}</span>
                          </li>
                        ))}
                      </ul>
                    </AnimatedCard>
                  )}
              </div>
            )}
          </PageTransition>
        </div>
      </div>
    </div>
  );
}
