import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { ArchitectureDiagram } from '../components/visual/ArchitectureDiagram';
import { FlowchartDiagram } from '../components/visual/FlowchartDiagram';
import { ERDiagram } from '../components/visual/ERDiagram';
import { SequenceDiagram } from '../components/visual/SequenceDiagram';
import { TradeoffSlider } from '../components/visual/TradeoffSlider';
import { AnimatedCard } from '../components/visual/AnimatedCard';
import { AnimatedCounter } from '../components/visual/AnimatedCounter';
import { Skeleton } from '../components/visual/Skeleton';
import type {
  ArchitectureDiagramData,
  TradeoffVisual,
  SeniorTopic,
} from '../components/visual/types';
import { SeniorTopicsPanel } from '../components/visual/SeniorTopicsPanel';
import { ArrowRight, Check, Lightbulb, BookOpen } from 'lucide-react';
import AppHeader from '../components/shell/AppHeader';
import DifficultyPill from '../components/shell/DifficultyPill';
import StatusAction from '../components/shell/StatusAction';
import BackLink from '../components/shell/BackLink';
import BottomSheet from '../components/shell/BottomSheet';
import InlineMarkdown from '../components/shell/InlineMarkdown';
import SectionNav, { type SectionNavItem } from '../components/shell/SectionNav';
import Zoomable from '../components/shell/Zoomable';
import { oneLineSummary } from '../lib/text';

interface SDQ {
  id: number;
  title: string;
  difficulty: string;
  description: string;
  hints: string[];
  constraints: string[];
  requirements_functional: string[];
  requirements_nonfunctional: string[];
  estimation: Record<string, string>;
  api_design: {
    endpoints?: { method: string; path: string; description: string; body?: string }[];
  };
  database_schema: { tables?: { name: string; columns: string[] }[]; indexes?: string[] };
  high_level_design: { description: string; components?: { name: string; role: string }[] };
  detailed_design: Record<string, string | Record<string, unknown>>;
  trade_offs: { option: string; recommendation: string; [key: string]: string }[];
  tips: string[];
  thought_process: string[];
  tags: string[];
  architecture_diagram?: ArchitectureDiagramData | null;
  sequence_diagram?: string | null;
  er_diagram?: string | null;
  thought_flow?: string | null;
  tradeoff_visual?: TradeoffVisual | null;
  senior_topics?: SeniorTopic[] | null;
}

const extractNumber = (s: string): number | null => {
  const m = s.match(/(\d{1,3}(?:,\d{3})+|\d+)/);
  if (!m) return null;
  const n = Number(m[1].replace(/,/g, ''));
  return Number.isFinite(n) ? n : null;
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

export default function SystemDesignDetail() {
  const { slug } = useParams<{ slug: string }>();
  const [q, setQ] = useState<SDQ | null>(null);
  const [loading, setLoading] = useState(true);
  const [referenceOpen, setReferenceOpen] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!slug) return;
    api
      .get<SDQ>(`/api/system-design/${slug}`)
      .then(setQ)
      .finally(() => setLoading(false));
  }, [slug]);

  const sectionItems = useMemo<SectionNavItem[]>(() => {
    if (!q) return [];
    const items: SectionNavItem[] = [];
    if (q.description) items.push({ id: 'prompt', label: 'Prompt' });
    const hasReqs =
      q.constraints.length > 0 ||
      q.requirements_functional.length > 0 ||
      q.requirements_nonfunctional.length > 0 ||
      Object.keys(q.estimation).length > 0;
    if (hasReqs) items.push({ id: 'requirements', label: 'Requirements' });
    if (q.thought_process.length > 0)
      items.push({ id: 'approach-framework', label: 'Approach framework' });
    if (q.thought_flow) items.push({ id: 'approach-map', label: 'Approach map' });
    if (q.trade_offs.length > 0 || q.tradeoff_visual)
      items.push({ id: 'trade-offs', label: 'Trade-offs' });
    const hasArch =
      q.architecture_diagram ||
      q.high_level_design.description ||
      Object.keys(q.detailed_design).length > 0;
    if (hasArch) items.push({ id: 'architecture', label: 'Architecture' });
    const hasDb =
      q.er_diagram ||
      (q.database_schema.tables && q.database_schema.tables.length > 0) ||
      (q.database_schema.indexes && q.database_schema.indexes.length > 0);
    if (hasDb) items.push({ id: 'database', label: 'Database' });
    const hasApi =
      q.sequence_diagram || (q.api_design.endpoints && q.api_design.endpoints.length > 0);
    if (hasApi) items.push({ id: 'api', label: 'API' });
    if (q.senior_topics && q.senior_topics.length > 0)
      items.push({ id: 'senior-topics', label: 'Senior topics' });
    return items;
  }, [q]);

  if (loading) {
    return (
      <div className="h-full p-6 space-y-3">
        <Skeleton width={220} height={20} />
        <Skeleton width={'100%'} height={14} />
        <Skeleton width={'80%'} height={14} />
        <Skeleton width={'90%'} height={14} />
      </div>
    );
  }

  if (!q) {
    return (
      <div className="flex items-center justify-center h-full">
        <div style={{ color: 'var(--text-3)', fontSize: 13 }}>
          Question not found.{' '}
          <Link to="/system-design/questions" style={{ color: 'var(--accent)' }}>
            Go back
          </Link>
        </div>
      </div>
    );
  }

  const hasRequirements =
    q.constraints.length > 0 ||
    q.requirements_functional.length > 0 ||
    q.requirements_nonfunctional.length > 0 ||
    Object.keys(q.estimation).length > 0;
  const hasArch =
    q.architecture_diagram ||
    q.high_level_design.description ||
    Object.keys(q.detailed_design).length > 0;
  const hasDb =
    q.er_diagram ||
    (q.database_schema.tables && q.database_schema.tables.length > 0) ||
    (q.database_schema.indexes && q.database_schema.indexes.length > 0);
  const hasApi =
    q.sequence_diagram || (q.api_design.endpoints && q.api_design.endpoints.length > 0);

  const hasReference = q.hints.length > 0 || q.tips.length > 0;

  // Extracted so we can render the same hints/tips cards in the
  // desktop sidebar and, on mobile, inside the BottomSheet reference
  // panel without duplicating ~60 lines of JSX.
  const referenceCards = (
    <>
      {q.hints.length > 0 && (
        <div
          className="card p-4"
          style={{ background: 'var(--bg-elev)' }}
        >
          <div
            className="eyebrow mb-3 inline-flex items-center gap-1.5"
            style={{ color: 'var(--accent)' }}
          >
            <Lightbulb size={11} strokeWidth={1.8} />
            Hints
          </div>
          <ol className="flex flex-col gap-2.5 list-none p-0 m-0">
            {q.hints.map((h, i) => (
              <li
                key={i}
                className="flex items-start gap-2"
                style={{ fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.5 }}
              >
                <span
                  className="mono"
                  style={{
                    color: 'var(--accent)',
                    fontSize: 10.5,
                    minWidth: 16,
                    flexShrink: 0,
                  }}
                >
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span>{h}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {q.tips.length > 0 && (
        <div className="card p-4" style={{ background: 'var(--bg-elev)' }}>
          <div
            className="eyebrow mb-3 inline-flex items-center gap-1.5"
            style={{ color: 'var(--ochre)' }}
          >
            <ArrowRight size={11} strokeWidth={1.8} />
            Tips
          </div>
          <ul className="flex flex-col gap-2 list-none p-0 m-0">
            {q.tips.map((tip, i) => (
              <li
                key={i}
                className="flex items-start gap-2"
                style={{ fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.5 }}
              >
                <span style={{ color: 'var(--ochre)', marginTop: 2 }}>·</span>
                <InlineMarkdown text={tip} />
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );

  return (
    <div className="h-full flex flex-col">
      <AppHeader
        title={q.title}
        description={oneLineSummary(q.description)}
        eyebrow={
          <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
            <BackLink to="/system-design/questions" />
            <DifficultyPill level={q.difficulty} />
          </span>
        }
        actions={<StatusAction kind="system" id={q.id} />}
        compactActions={<StatusAction kind="system" id={q.id} compact />}
      />

      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto">
        <div className="px-5 sm:px-8 py-6 lg:py-8 grid gap-8 lg:gap-10 grid-cols-1 lg:[grid-template-columns:minmax(0,1fr)_300px]">
          <main className="space-y-12 min-w-0">
            {q.description && (
              <section>
                <SectionHeading id="prompt">Prompt</SectionHeading>
                <AnimatedCard className="card" style={{ padding: 24 }}>
                  <p
                    style={{
                      margin: 0,
                      color: 'var(--text-2)',
                      fontSize: 14.5,
                      lineHeight: 1.65,
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {q.description}
                  </p>
                </AnimatedCard>
              </section>
            )}

            {hasRequirements && (
              <section>
                <SectionHeading id="requirements">Requirements</SectionHeading>
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 auto-rows-min">
                  {q.constraints.length > 0 && (
                    <AnimatedCard className="card p-5 lg:col-span-7">
                      <h3 className="eyebrow mb-3">Constraints</h3>
                      <ul className="flex flex-col gap-2">
                        {q.constraints.map((c, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-2"
                            style={{ fontSize: 13, color: 'var(--text-2)' }}
                          >
                            <span style={{ color: 'var(--text-4)' }}>•</span>
                            <InlineMarkdown text={c} />
                          </li>
                        ))}
                      </ul>
                    </AnimatedCard>
                  )}
                  {Object.entries(q.estimation).length > 0 && (
                    <AnimatedCard
                      className={`card p-4 ${
                        q.constraints.length > 0 ? 'lg:col-span-5' : 'lg:col-span-12'
                      }`}
                    >
                      <h3 className="eyebrow mb-3">Estimation</h3>
                      <table className="w-full" style={{ fontSize: 13 }}>
                        <tbody>
                          {Object.entries(q.estimation).map(([key, value]) => {
                            const n = extractNumber(value);
                            return (
                              <tr
                                key={key}
                                style={{ borderBottom: '1px solid var(--border)' }}
                              >
                                <td
                                  className="mono uppercase"
                                  style={{
                                    padding: '10px 12px 10px 0',
                                    color: 'var(--text-3)',
                                    fontSize: 10.5,
                                    letterSpacing: '0.1em',
                                    width: 180,
                                  }}
                                >
                                  {key.replace(/_/g, ' ')}
                                </td>
                                <td style={{ padding: '10px 0', color: 'var(--text-2)' }}>
                                  {n !== null ? (
                                    <span>
                                      <AnimatedCounter
                                        value={n}
                                        duration={1.0}
                                        className="font-mono"
                                      />
                                      <span style={{ marginLeft: 4, color: 'var(--text-3)' }}>
                                        {value.replace(/(\d{1,3}(?:,\d{3})+|\d+)/, '').trim()}
                                      </span>
                                    </span>
                                  ) : (
                                    value
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </AnimatedCard>
                  )}
                  {q.requirements_functional.length > 0 && (
                    <AnimatedCard className="card p-5 lg:col-span-6">
                      <h3 className="eyebrow mb-3">Functional</h3>
                      <ul className="flex flex-col gap-2">
                        {q.requirements_functional.map((r, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-2.5"
                            style={{ fontSize: 13, color: 'var(--text-2)' }}
                          >
                            <Check
                              size={14}
                              strokeWidth={2}
                              style={{ color: 'var(--forest)', marginTop: 2, flexShrink: 0 }}
                            />
                            <InlineMarkdown text={r} />
                          </li>
                        ))}
                      </ul>
                    </AnimatedCard>
                  )}
                  {q.requirements_nonfunctional.length > 0 && (
                    <AnimatedCard className="card p-5 lg:col-span-6" delay={0.05}>
                      <h3 className="eyebrow mb-3">Non-functional</h3>
                      <ul className="flex flex-col gap-2">
                        {q.requirements_nonfunctional.map((r, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-2.5"
                            style={{ fontSize: 13, color: 'var(--text-2)' }}
                          >
                            <Check
                              size={14}
                              strokeWidth={2}
                              style={{ color: 'var(--accent)', marginTop: 2, flexShrink: 0 }}
                            />
                            <InlineMarkdown text={r} />
                          </li>
                        ))}
                      </ul>
                    </AnimatedCard>
                  )}
                </div>
              </section>
            )}

            {q.thought_process.length > 0 && (
              <section>
                <SectionHeading id="approach-framework">Approach framework</SectionHeading>
                <AnimatedCard className="card p-6">
                  <ol className="flex flex-col gap-3">
                    {q.thought_process.map((step, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-3"
                        style={{ fontSize: 14, color: 'var(--text-2)', lineHeight: 1.6 }}
                      >
                        <span
                          className="mono"
                          style={{
                            color: 'var(--text-4)',
                            width: 28,
                            flexShrink: 0,
                            paddingTop: 2,
                          }}
                        >
                          {String(i + 1).padStart(2, '0')}.
                        </span>
                        <InlineMarkdown text={step} />
                      </li>
                    ))}
                  </ol>
                </AnimatedCard>
              </section>
            )}

            {q.thought_flow && (
              <section>
                <SectionHeading id="approach-map">Approach map</SectionHeading>
                <AnimatedCard className="card p-4 overflow-hidden">
                  <Zoomable label="Approach map">
                    <FlowchartDiagram source={q.thought_flow} />
                  </Zoomable>
                </AnimatedCard>
              </section>
            )}

            {(q.trade_offs.length > 0 || q.tradeoff_visual) && (
              <section>
                <SectionHeading id="trade-offs">Trade-offs</SectionHeading>
                {q.tradeoff_visual && (
                  <div className="mb-5">
                    <Zoomable label="Trade-off comparison">
                      <TradeoffSlider visual={q.tradeoff_visual} />
                    </Zoomable>
                  </div>
                )}
                {q.trade_offs.length > 0 && (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {q.trade_offs.map((t, i) => {
                      const keys = Object.keys(t).filter(
                        (k) => k !== 'option' && k !== 'recommendation' && t[k],
                      );
                      return (
                        <AnimatedCard key={i} className="card p-4" delay={i * 0.04}>
                          <h3 style={{ fontSize: 15, fontWeight: 500, marginBottom: 12 }}>
                            {t.option}
                          </h3>
                          <div className="space-y-2">
                            {keys.map((k) => (
                              <div key={k} className="flex items-start gap-2">
                                <span
                                  className="mono uppercase"
                                  style={{
                                    fontSize: 10.5,
                                    color: 'var(--text-4)',
                                    width: 110,
                                    flexShrink: 0,
                                    letterSpacing: '0.1em',
                                  }}
                                >
                                  {k.replace(/^(for_|against_)/, '').replace(/_/g, ' ')}
                                </span>
                                <span style={{ fontSize: 13, color: 'var(--text-2)' }}>
                                  {t[k]}
                                </span>
                              </div>
                            ))}
                          </div>
                          <div
                            className="mt-3 pt-3"
                            style={{ borderTop: '1px solid var(--border)' }}
                          >
                            <span
                              className="mono uppercase"
                              style={{
                                fontSize: 10.5,
                                color: 'var(--text-3)',
                                letterSpacing: '0.1em',
                              }}
                            >
                              Recommendation
                            </span>
                            <span
                              style={{
                                fontSize: 13.5,
                                color: 'var(--text-2)',
                                marginLeft: 8,
                              }}
                            >
                              {t.recommendation}
                            </span>
                          </div>
                        </AnimatedCard>
                      );
                    })}
                  </div>
                )}
              </section>
            )}

            {hasArch && (
              <section>
                <SectionHeading id="architecture">Architecture</SectionHeading>
                {q.architecture_diagram && (
                  <AnimatedCard className="card overflow-hidden mb-5">
                    <Zoomable label="Architecture diagram">
                      <ArchitectureDiagram data={q.architecture_diagram} height={460} />
                    </Zoomable>
                  </AnimatedCard>
                )}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                  <div className="lg:col-span-5 space-y-3">
                    {q.high_level_design.description && (
                      <p style={{ fontSize: 14.5, color: 'var(--text-2)', lineHeight: 1.65 }}>
                        {q.high_level_design.description}
                      </p>
                    )}
                    {q.high_level_design.components &&
                      q.high_level_design.components.length > 0 && (
                        <div className="space-y-2">
                          <h3 className="eyebrow">Components</h3>
                          {q.high_level_design.components.map((comp, i) => (
                            <AnimatedCard key={i} className="card p-3" delay={i * 0.04}>
                              <div className="flex items-start gap-3">
                                <span
                                  className="mono"
                                  style={{
                                    color: 'var(--text-4)',
                                    width: 20,
                                    flexShrink: 0,
                                  }}
                                >
                                  {String(i + 1).padStart(2, '0')}
                                </span>
                                <div>
                                  <div style={{ fontSize: 14, fontWeight: 500 }}>
                                    {comp.name}
                                  </div>
                                  <p
                                    style={{
                                      fontSize: 12.5,
                                      color: 'var(--text-3)',
                                      marginTop: 2,
                                      lineHeight: 1.5,
                                    }}
                                  >
                                    {comp.role}
                                  </p>
                                </div>
                              </div>
                            </AnimatedCard>
                          ))}
                        </div>
                      )}
                  </div>
                  {Object.keys(q.detailed_design).length > 0 && (
                    <div className="lg:col-span-7 space-y-2">
                      <h3 className="eyebrow">Deep dive</h3>
                      {Object.entries(q.detailed_design).map(([key, value], i) => (
                        <AnimatedCard key={key} className="card p-3" delay={i * 0.04}>
                          <span
                            className="mono uppercase"
                            style={{
                              fontSize: 10.5,
                              color: 'var(--accent)',
                              letterSpacing: '0.12em',
                            }}
                          >
                            {key.replace(/_/g, ' ')}
                          </span>
                          {typeof value === 'string' ? (
                            <p
                              style={{
                                fontSize: 13.5,
                                color: 'var(--text-2)',
                                marginTop: 6,
                                lineHeight: 1.6,
                              }}
                            >
                              {value}
                            </p>
                          ) : value && typeof value === 'object' ? (
                            <div className="flex flex-col gap-2" style={{ marginTop: 8 }}>
                              {Object.entries(value as Record<string, unknown>).map(
                                ([subKey, subValue]) => (
                                  <div
                                    key={subKey}
                                    style={{
                                      paddingTop: 6,
                                      borderTop: '1px dashed var(--border)',
                                    }}
                                  >
                                    <span
                                      className="mono uppercase"
                                      style={{
                                        fontSize: 10,
                                        color: 'var(--text-4)',
                                        letterSpacing: '0.1em',
                                      }}
                                    >
                                      {subKey.replace(/_/g, ' ')}
                                    </span>
                                    <p
                                      style={{
                                        fontSize: 13,
                                        color: 'var(--text-2)',
                                        marginTop: 4,
                                        lineHeight: 1.55,
                                      }}
                                    >
                                      {typeof subValue === 'string'
                                        ? subValue
                                        : JSON.stringify(subValue)}
                                    </p>
                                  </div>
                                ),
                              )}
                            </div>
                          ) : null}
                        </AnimatedCard>
                      ))}
                    </div>
                  )}
                </div>
              </section>
            )}

            {hasDb && (
              <section>
                <SectionHeading id="database">Database</SectionHeading>
                {q.er_diagram && (
                  <AnimatedCard className="card p-5 overflow-hidden mb-5">
                    <h3 className="eyebrow mb-3">Schema relationships</h3>
                    <Zoomable label="Schema relationships">
                      <ERDiagram source={q.er_diagram} />
                    </Zoomable>
                  </AnimatedCard>
                )}
                {q.database_schema.tables && q.database_schema.tables.length > 0 && (
                  <div
                    className="grid gap-3"
                    style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}
                  >
                    {q.database_schema.tables.map((table, i) => (
                      <AnimatedCard key={i} className="card overflow-hidden" delay={i * 0.04}>
                        <div
                          className="flex items-center justify-between"
                          style={{
                            padding: '12px 16px',
                            background: 'var(--bg-sunken)',
                            borderBottom: '1px solid var(--border)',
                          }}
                        >
                          <div className="flex items-center gap-2">
                            <span
                              style={{
                                width: 6,
                                height: 6,
                                borderRadius: 999,
                                background: 'var(--accent)',
                              }}
                            />
                            <span className="eyebrow" style={{ fontSize: 9.5 }}>
                              Table
                            </span>
                          </div>
                          <span
                            className="mono"
                            style={{ fontSize: 10.5, color: 'var(--text-4)' }}
                          >
                            {table.columns.length} cols
                          </span>
                        </div>
                        <div style={{ padding: '14px 16px' }}>
                          <h3
                            className="display-italic"
                            style={{
                              fontSize: 20,
                              fontWeight: 400,
                              lineHeight: 1.1,
                              marginBottom: 10,
                            }}
                          >
                            {table.name}
                          </h3>
                          <div className="flex flex-col" style={{ rowGap: 6 }}>
                            {table.columns.map((col, j) => {
                              const [name, ...rest] = col.split(/\s+/);
                              const typeLabel = rest.join(' ');
                              return (
                                <div
                                  key={j}
                                  className="flex items-baseline justify-between gap-3"
                                  style={{
                                    padding: '4px 0',
                                    borderBottom:
                                      j < table.columns.length - 1
                                        ? '1px dashed var(--border)'
                                        : 'none',
                                  }}
                                >
                                  <span
                                    className="mono"
                                    style={{ fontSize: 11.5, color: 'var(--text-2)' }}
                                  >
                                    {name}
                                  </span>
                                  {typeLabel && (
                                    <span
                                      className="mono uppercase"
                                      style={{
                                        fontSize: 9.5,
                                        color: 'var(--text-4)',
                                        letterSpacing: '0.08em',
                                        textAlign: 'right',
                                      }}
                                    >
                                      {typeLabel}
                                    </span>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </AnimatedCard>
                    ))}
                  </div>
                )}
                {q.database_schema.indexes && q.database_schema.indexes.length > 0 && (
                  <AnimatedCard className="card p-5 mt-4">
                    <h3 className="eyebrow mb-3">Indexes</h3>
                    <div className="flex flex-wrap gap-2">
                      {q.database_schema.indexes.map((idx, i) => (
                        <span
                          key={i}
                          className="pill"
                          style={{
                            background: 'var(--accent-soft)',
                            color: 'var(--accent)',
                          }}
                        >
                          {idx}
                        </span>
                      ))}
                    </div>
                  </AnimatedCard>
                )}
              </section>
            )}

            {hasApi && (
              <section>
                <SectionHeading id="api">API</SectionHeading>
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                  {q.sequence_diagram && (
                    <AnimatedCard className="lg:col-span-7 card p-4 overflow-hidden">
                      <h3 className="eyebrow mb-3">Request flow</h3>
                      <Zoomable label="Request flow">
                        <SequenceDiagram source={q.sequence_diagram} />
                      </Zoomable>
                    </AnimatedCard>
                  )}
                  <div
                    className={
                      q.sequence_diagram
                        ? 'lg:col-span-5 space-y-2'
                        : 'lg:col-span-12 space-y-2'
                    }
                  >
                    {q.api_design.endpoints &&
                      q.api_design.endpoints.length > 0 &&
                      q.api_design.endpoints.map((ep, i) => (
                        <AnimatedCard key={i} className="card p-3" delay={i * 0.04}>
                          <div className="flex items-center gap-3 flex-wrap">
                            <span
                              className="mono"
                              style={{
                                fontSize: 10.5,
                                fontWeight: 600,
                                padding: '3px 7px',
                                borderRadius: 4,
                                background: 'var(--ink)',
                                color: 'var(--paper)',
                              }}
                            >
                              {ep.method}
                            </span>
                            <span
                              className="mono"
                              style={{
                                fontSize: 13,
                                color: 'var(--text-2)',
                                wordBreak: 'break-all',
                              }}
                            >
                              {ep.path}
                            </span>
                          </div>
                          <p style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 6 }}>
                            {ep.description}
                          </p>
                          {ep.body && (
                            <pre
                              className="mono"
                              style={{
                                fontSize: 12,
                                background: 'var(--bg-sunken)',
                                borderRadius: 6,
                                padding: 10,
                                marginTop: 8,
                                color: 'var(--text-2)',
                                overflowX: 'auto',
                              }}
                            >
                              {ep.body}
                            </pre>
                          )}
                        </AnimatedCard>
                      ))}
                  </div>
                </div>
              </section>
            )}

            {q.senior_topics && q.senior_topics.length > 0 && (
              <section>
                <SectionHeading id="senior-topics">Senior topics</SectionHeading>
                <SeniorTopicsPanel topics={q.senior_topics} />
              </section>
            )}
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

      {/* Mobile-only floating trigger + bottom sheet for the Hints /
          Tips reference material that otherwise sits in the desktop
          sidebar. Matches the Option C pattern used on the Coding
          detail page. */}
      {hasReference && (
        <>
          <button
            type="button"
            onClick={() => setReferenceOpen(true)}
            aria-label="Open hints and tips"
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
            Reference
          </button>
          <BottomSheet
            open={referenceOpen}
            onClose={() => setReferenceOpen(false)}
            title="Hints & Tips"
          >
            {referenceCards}
          </BottomSheet>
        </>
      )}
    </div>
  );
}
