import { useEffect, useRef, useState } from 'react';
import { useParams, useLocation, Link, NavLink } from 'react-router-dom';
import SDPracticeView from './sd-practice/SDPracticeView';
import { getSystemDesignQuestion } from '../content/api';
import { ArchitectureDiagram } from '../components/visual/ArchitectureDiagram';
import { FlowchartDiagram } from '../components/visual/FlowchartDiagram';
import { ERDiagram } from '../components/visual/ERDiagram';
import { SequenceDiagram } from '../components/visual/SequenceDiagram';
import { TradeoffSlider } from '../components/visual/TradeoffSlider';
import { AnimatedCard } from '../components/visual/AnimatedCard';
import { Skeleton } from '../components/visual/Skeleton';
import type {
  ArchitectureDiagramData,
  TradeoffVisual,
  SeniorTopic,
} from '../components/visual/types';
import { SeniorTopicsPanel } from '../components/visual/SeniorTopicsPanel';
import { Check, ChevronUp, ChevronDown } from 'lucide-react';
import AppHeader from '../components/shell/AppHeader';
import DifficultyPill from '../components/shell/DifficultyPill';
import StatusAction from '../components/shell/StatusAction';
import BackLink from '../components/shell/BackLink';
import InlineMarkdown from '../components/shell/InlineMarkdown';
import BlockMarkdown from '../components/shell/BlockMarkdown';
import Zoomable from '../components/shell/Zoomable';
import { Section } from './guides/shared/primitives';

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

export default function SystemDesignDetail() {
  const { slug } = useParams<{ slug: string }>();
  const location = useLocation();
  const tab: 'practice' | 'guidance' = location.pathname.endsWith('/guidance') ? 'guidance' : 'practice';
  const [q, setQ] = useState<SDQ | null>(null);
  const [loading, setLoading] = useState(true);
  const headerStorageKey = slug ? `rounds.sd.detail.${slug}.headerCollapsed` : '';
  const [headerCollapsed, setHeaderCollapsed] = useState<boolean>(() => {
    if (typeof window === 'undefined' || !headerStorageKey) return false;
    return window.localStorage.getItem(headerStorageKey) === '1';
  });
  useEffect(() => {
    if (!headerStorageKey || typeof window === 'undefined') return;
    window.localStorage.setItem(headerStorageKey, headerCollapsed ? '1' : '0');
  }, [headerCollapsed, headerStorageKey]);

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!slug) return;
    getSystemDesignQuestion<SDQ>(slug)
      .then(setQ)
      .finally(() => setLoading(false));
  }, [slug]);

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

  return (
    <div className="h-full flex flex-col">
      <AppHeader
        title={q.title}
        eyebrow={
          <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
            <BackLink to="/system-design/questions" />
            <DifficultyPill level={q.difficulty} />
          </span>
        }
        chromeActions={<StatusAction kind="system" id={q.id} />}
        compactActions={<StatusAction kind="system" id={q.id} compact />}
        timer={q ? { kind: 'system', id: q.id } : undefined}
      />

      <PromptHeader
        q={q}
        hasRequirements={hasRequirements}
        collapsed={headerCollapsed}
        onToggle={() => setHeaderCollapsed((v) => !v)}
      />

      <TabStrip slug={slug ?? ''} active={tab} />

      {tab === 'practice' ? (
        <div className="flex-1 min-h-0 overflow-hidden">
          <SDPracticeView
            questionSlug={slug ?? ''}
            questionPrompt={q.description}
          />
        </div>
      ) : (
      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto">
        <div
          className="grid"
          style={{
            gap: 'var(--gap-lg)',
            padding: 'var(--gap-lg) var(--page-pad-x)',
            width: '100%',
            minWidth: 0,
          }}
        >
            {q.thought_process.length > 0 && (
              <Section id="approach-framework" title="Approach framework">
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
              </Section>
            )}

            {q.thought_flow && (
              <Section id="approach-map" title="Approach map">
                <AnimatedCard className="card p-4 overflow-hidden">
                  <Zoomable label="Approach map">
                    <FlowchartDiagram source={q.thought_flow} />
                  </Zoomable>
                </AnimatedCard>
              </Section>
            )}

            {(q.trade_offs.length > 0 || q.tradeoff_visual) && (
              <Section id="trade-offs" title="Trade-offs">
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
              </Section>
            )}

            {hasArch && (
              <Section id="architecture" title="Architecture">
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
              </Section>
            )}

            {hasDb && (
              <Section id="database" title="Database">
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
              </Section>
            )}

            {hasApi && (
              <Section id="api" title="API">
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
              </Section>
            )}

            {q.senior_topics && q.senior_topics.length > 0 && (
              <Section id="senior-topics" title="Senior topics">
                <SeniorTopicsPanel topics={q.senior_topics} />
              </Section>
            )}

            {q.hints.length > 0 && (
              <Section id="hints" title="Hints">
                <ol className="flex flex-col gap-2.5 list-none p-0 m-0">
                  {q.hints.map((h, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2"
                      style={{ fontSize: 13.5, color: 'var(--text-2)', lineHeight: 1.55 }}
                    >
                      <span
                        className="mono"
                        style={{
                          color: 'var(--accent)',
                          fontSize: 11,
                          minWidth: 20,
                          flexShrink: 0,
                        }}
                      >
                        {String(i + 1).padStart(2, '0')}
                      </span>
                      <span>{h}</span>
                    </li>
                  ))}
                </ol>
              </Section>
            )}

            {q.tips.length > 0 && (
              <Section id="tips" title="Tips">
                <ul className="flex flex-col gap-2 list-none p-0 m-0">
                  {q.tips.map((tip, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2"
                      style={{ fontSize: 13.5, color: 'var(--text-2)', lineHeight: 1.55 }}
                    >
                      <span style={{ color: 'var(--ochre)', marginTop: 2 }}>·</span>
                      <InlineMarkdown text={tip} />
                    </li>
                  ))}
                </ul>
              </Section>
            )}
        </div>
      </div>
      )}
    </div>
  );
}

function TabStrip({ slug, active }: { slug: string; active: 'practice' | 'guidance' }) {
  const tabs: { id: typeof active; label: string; to: string }[] = [
    { id: 'practice', label: 'Practice', to: `/system-design/question/${slug}` },
    { id: 'guidance', label: 'Guidance', to: `/system-design/question/${slug}/guidance` },
  ];
  return (
    <div
      role="tablist"
      style={{
        display: 'flex',
        gap: 0,
        borderBottom: '1px solid var(--border)',
        padding: '0 var(--page-pad-x)',
        background: 'var(--bg)',
      }}
    >
      {tabs.map((t) => (
        <NavLink
          key={t.id}
          to={t.to}
          end={t.id === 'practice'}
          role="tab"
          aria-selected={active === t.id}
          style={() => ({
            padding: '10px 14px',
            fontSize: 13,
            fontWeight: 600,
            color: active === t.id ? 'var(--text)' : 'var(--text-3)',
            borderBottom:
              active === t.id ? '2px solid var(--accent)' : '2px solid transparent',
            textDecoration: 'none',
            marginBottom: -1,
          })}
        >
          {t.label}
        </NavLink>
      ))}
    </div>
  );
}

function PromptHeader({
  q,
  hasRequirements,
  collapsed,
  onToggle,
}: {
  q: SDQ;
  hasRequirements: boolean;
  collapsed: boolean;
  onToggle: () => void;
}) {
  // Shared toggle pill — top-right of the header in BOTH states so the
  // click target doesn't jump as the user toggles. Chevron + label swap
  // for visual hint (Show ↓ / Hide ↑).
  const toggleButton = (
    <button
      type="button"
      onClick={onToggle}
      style={{
        background: 'transparent',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '4px 10px',
        fontSize: 11.5,
        color: 'var(--text-3)',
        cursor: 'pointer',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        flexShrink: 0,
      }}
      aria-expanded={!collapsed}
      aria-label={collapsed ? 'Show prompt and requirements' : 'Hide prompt and requirements'}
    >
      {collapsed ? <ChevronDown size={12} strokeWidth={2} /> : <ChevronUp size={12} strokeWidth={2} />}
      {collapsed ? 'Show' : 'Hide'}
    </button>
  );

  if (collapsed) {
    return (
      <div
        style={{
          padding: '8px var(--page-pad-x)',
          background: 'var(--bg-elev)',
          borderBottom: '1px solid var(--border)',
          color: 'var(--text-3)',
          fontSize: 12.5,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <span style={{ fontWeight: 600, color: 'var(--text-2)', flexShrink: 0 }}>
          Prompt &amp; requirements
        </span>
        <span style={{ color: 'var(--text-4)' }}>·</span>
        <span
          style={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flex: 1,
            minWidth: 0,
          }}
        >
          {q.description.replace(/\s+/g, ' ').slice(0, 140)}
          {q.description.length > 140 ? '…' : ''}
        </span>
        {toggleButton}
      </div>
    );
  }

  return (
    <div
      style={{
        padding: 'var(--pad-md) var(--page-pad-x)',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--gap-sm)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span
          className="eyebrow"
          style={{ fontSize: 11, color: 'var(--text-3)', letterSpacing: '0.12em' }}
        >
          Prompt
        </span>
        <span style={{ marginLeft: 'auto' }}>{toggleButton}</span>
      </div>

      {q.description && (
        <BlockMarkdown
          text={q.description}
          style={{
            color: 'var(--text-2)',
            fontSize: 14,
            lineHeight: 1.6,
            margin: 0,
          }}
        />
      )}

      {hasRequirements && (
        <div
          className="grid grid-cols-1 lg:grid-cols-12"
          style={{ gap: 'var(--gap-sm)', marginTop: 4 }}
        >
          {q.constraints.length > 0 && (
            <div className="card lg:col-span-7" style={{ padding: 'var(--pad-sm)' }}>
              <h3 className="eyebrow" style={{ marginBottom: 6, fontSize: 10.5 }}>Constraints</h3>
              <ul className="flex flex-col gap-1">
                {q.constraints.map((c, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2"
                    style={{ fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.5 }}
                  >
                    <span style={{ color: 'var(--text-4)' }}>•</span>
                    <InlineMarkdown text={c} />
                  </li>
                ))}
              </ul>
            </div>
          )}
          {Object.entries(q.estimation).length > 0 && (
            <div
              className={`card ${q.constraints.length > 0 ? 'lg:col-span-5' : 'lg:col-span-12'}`}
              style={{ padding: 'var(--pad-sm)' }}
            >
              <h3 className="eyebrow" style={{ marginBottom: 6, fontSize: 10.5 }}>Estimation</h3>
              <table className="w-full" style={{ fontSize: 12.5 }}>
                <tbody>
                  {Object.entries(q.estimation).map(([key, value]) => (
                    <tr key={key} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td
                        className="mono uppercase"
                        style={{
                          padding: '6px 10px 6px 0',
                          color: 'var(--text-3)',
                          fontSize: 10,
                          letterSpacing: '0.1em',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {key.replace(/_/g, ' ')}
                      </td>
                      <td style={{ padding: '6px 0', color: 'var(--text-2)' }}>{value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {q.requirements_functional.length > 0 && (
            <div className="card lg:col-span-6" style={{ padding: 'var(--pad-sm)' }}>
              <h3 className="eyebrow" style={{ marginBottom: 6, fontSize: 10.5 }}>Functional</h3>
              <ul className="flex flex-col gap-1">
                {q.requirements_functional.map((r, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2"
                    style={{ fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.5 }}
                  >
                    <Check
                      size={12}
                      strokeWidth={2}
                      style={{ color: 'var(--forest)', marginTop: 3, flexShrink: 0 }}
                    />
                    <InlineMarkdown text={r} />
                  </li>
                ))}
              </ul>
            </div>
          )}
          {q.requirements_nonfunctional.length > 0 && (
            <div className="card lg:col-span-6" style={{ padding: 'var(--pad-sm)' }}>
              <h3 className="eyebrow" style={{ marginBottom: 6, fontSize: 10.5 }}>Non-functional</h3>
              <ul className="flex flex-col gap-1">
                {q.requirements_nonfunctional.map((r, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2"
                    style={{ fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.5 }}
                  >
                    <Check
                      size={12}
                      strokeWidth={2}
                      style={{ color: 'var(--accent)', marginTop: 3, flexShrink: 0 }}
                    />
                    <InlineMarkdown text={r} />
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
