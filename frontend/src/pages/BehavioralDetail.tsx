import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowRight, BookOpen, Check, X } from 'lucide-react';
import {
  getBehavioralQuestion,
  listBehavioralCategories,
  listBehavioralQuestions,
} from '../content/api';
import { oneLineSummary } from '../lib/text';
import { AnimatedCard } from '../components/visual/AnimatedCard';
import { Skeleton } from '../components/visual/Skeleton';
import { MyAnecdotesPanel } from './behavioral/MyAnecdotesPanel';
import type { BehavioralQuestionLite } from './behavioral/types';
import AppHeader from '../components/shell/AppHeader';
import StatusAction from '../components/shell/StatusAction';
import BackLink from '../components/shell/BackLink';
import BottomSheet from '../components/shell/BottomSheet';
import SectionNav, { type SectionNavItem } from '../components/shell/SectionNav';

interface BC {
  id: string;
  name: string;
  description: string;
  color: string;
  icon: string;
}

interface BQ {
  id: string;
  title: string;
  question_text: string;
  category_ids: string[];
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
        fontSize: 'clamp(22px, 5.5vw, 30px)',
        fontWeight: 400,
        lineHeight: 1.1,
        margin: '0 0 14px',
        scrollMarginTop: 24,
      }}
    >
      {children}
    </h2>
  );
}

export default function BehavioralDetail() {
  const { slug } = useParams<{ slug: string }>();
  const [q, setQ] = useState<BQ | null>(null);
  const [categories, setCategories] = useState<BC[]>([]);
  const [allQuestions, setAllQuestions] = useState<BehavioralQuestionLite[]>([]);
  const [loading, setLoading] = useState(true);
  const [referenceOpen, setReferenceOpen] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!slug) return;
    Promise.all([
      getBehavioralQuestion<BQ>(slug),
      listBehavioralCategories<BC>(),
      listBehavioralQuestions<{ id: string; title: string }>(),
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
          <Link to="/behavioral/questions" style={{ color: 'var(--accent)' }}>
            Go back
          </Link>
        </div>
      </div>
    );
  }

  const getCat = (cid: string) => categories.find((c) => c.id === cid);
  const hasStar =
    !!(q.star_guide.situation || q.star_guide.task || q.star_guide.action || q.star_guide.result);
  const hasSample =
    !!(
      q.sample_response.situation ||
      q.sample_response.task ||
      q.sample_response.action ||
      q.sample_response.result
    );

  const hasReference =
    q.follow_up_questions.length > 0 ||
    q.tips.length > 0 ||
    q.common_pitfalls.length > 0 ||
    (q.sample_response.key_strengths_shown &&
      q.sample_response.key_strengths_shown.length > 0) ||
    q.what_interviewers_look_for.length > 0;

  // Extracted so the desktop sidebar and the mobile BottomSheet share
  // the same DOM. Order matters — it matches the sidebar's reading
  // order: likely follow-ups → do/don't → strengths → interviewers.
  const referenceCards = (
    <>
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
    </>
  );

  const categoryPills = q.category_ids
    .map((cid) => getCat(cid))
    .filter((c): c is BC => Boolean(c));

  return (
    <div className="h-full flex flex-col">
      <AppHeader
        title={q.title}
        description={oneLineSummary(q.question_text)}
        eyebrow={
          <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
            <BackLink to="/behavioral/questions" />
            {categoryPills.map((c) => (
              <span
                key={c.id}
                className="pill"
                style={{
                  background: 'transparent',
                  color: c.color,
                  boxShadow: `inset 0 0 0 1px ${c.color}`,
                }}
              >
                {c.name}
              </span>
            ))}
          </span>
        }
        chromeActions={<StatusAction kind="behavioral" id={q.id} />}
        compactActions={<StatusAction kind="behavioral" id={q.id} compact />}
        timer={q ? { kind: 'behavioral', id: q.id } : undefined}
      />

      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto">
        <div className="px-5 sm:px-8 py-6 lg:py-8 grid gap-8 lg:gap-10 grid-cols-1 lg:[grid-template-columns:minmax(0,1fr)_300px]">
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

          <aside className="hidden lg:block lg:min-w-0">
            <div className="lg:sticky lg:top-4 flex flex-col gap-4 lg:max-h-[calc(100vh-32px)]">
              <div
                className="hidden lg:block"
                style={{ background: 'var(--bg)', flexShrink: 0, paddingBottom: 4 }}
              >
                <SectionNav items={sectionItems} scrollContainer={scrollRef} nonSticky />
              </div>
              <div className="space-y-5 lg:overflow-y-auto lg:pr-1 lg:min-h-0">
                {referenceCards}
              </div>
            </div>
          </aside>
        </div>
      </div>

      {/* Mobile-only trigger + bottom sheet for the study reference
          material (follow-ups, do/don't, strengths, interviewer look-
          fors) that sits in the desktop sidebar. Matches Option C. */}
      {hasReference && (
        <>
          <button
            type="button"
            onClick={() => setReferenceOpen(true)}
            aria-label="Open study notes"
            className="detail-reference-fab lg:hidden inline-flex items-center gap-1.5"
            style={{
              padding: '11px 16px',
              border: 0,
              borderRadius: 999,
              background: 'var(--accent)',
              color: 'var(--bg-elev)',
              fontSize: 13,
              fontWeight: 600,
              boxShadow:
                '0 6px 16px -4px rgba(24,22,19,0.35), 0 0 0 1px rgba(24,22,19,0.1)',
              cursor: 'pointer',
            }}
          >
            <BookOpen size={13} strokeWidth={2} />
            Study notes
          </button>
          <BottomSheet
            open={referenceOpen}
            onClose={() => setReferenceOpen(false)}
            title="Study notes"
          >
            {referenceCards}
          </BottomSheet>
        </>
      )}
    </div>
  );
}
