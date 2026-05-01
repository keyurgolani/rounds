import type { RefObject } from 'react';
import { Clock3, Database, GitBranch, Layers3, ListChecks, Route, ShieldCheck } from 'lucide-react';
import AppHeader from '../../components/shell/AppHeader';
import type { SectionNavItem } from '../../components/shell/SectionNav';
import type { GuideConfig, GuideRecord } from './guideTypes';
import {
  ChecklistChips,
  DecisionLaneGrid,
  FormulaCard,
  getGuidePages,
  getSection,
  GuideCommandStrip,
  GuidePageCard,
  GuideRightRailLayout,
  PracticeFocusedPage,
  TimelineCards,
  WarActionList,
  WarHeading,
  warCardStyle,
} from './GuideShared';

const decisionLanes = [
  {
    title: 'Cache Decision',
    signal: 'Repeated read, hot object, or p95 pressure',
    move: 'Use cache-aside first; name TTL, invalidation, and stampede control.',
    icon: Layers3,
  },
  {
    title: 'Async Decision',
    signal: 'Slow work, bursty writes, notifications, fanout, indexing',
    move: 'Add a queue with idempotent workers, DLQ, retry budget, and lag metric.',
    icon: Route,
  },
  {
    title: 'Storage Decision',
    signal: 'Access pattern decides the database, not trend or preference',
    move: 'State entities, primary key, secondary indexes, shard key, retention.',
    icon: Database,
  },
  {
    title: 'Reliability Decision',
    signal: 'Duplicate write, partial failure, hot key, outage, backlog',
    move: 'Pick one failure and give the mitigation plus the metric that detects it.',
    icon: ShieldCheck,
  },
];

const timeline = [
  { time: '0-5 MIN', label: 'Clarify', detail: 'Users, top actions, scale, SLOs, consistency, non-goals.' },
  { time: '5-10 MIN', label: 'Shape', detail: 'APIs and data model before infrastructure boxes.' },
  { time: '10-20 MIN', label: 'Paths', detail: 'Draw write path and read path with labeled arrows.' },
  { time: '20-32 MIN', label: 'Deep Dive', detail: 'Pick the bottleneck the requirements force.' },
  { time: '32-40 MIN', label: 'Break It', detail: 'Retries, idempotency, backpressure, failover, hot keys.' },
  { time: '40-45 MIN', label: 'Close', detail: 'Requirements met, trade-offs, and next improvements.' },
];

function SystemDesignOverview({ guide, config, scrollRef }: { guide: GuideRecord; config: GuideConfig; scrollRef: RefObject<HTMLDivElement> }) {
  const guidePages = getGuidePages(guide);
  const capacity = getSection(guide, 'capacity-math');
  const opening = getSection(guide, 'opening-script');
  const designOrder = getSection(guide, 'design-order');
  const sectionItems: SectionNavItem[] = [
    { id: 'war-room', label: 'War room' },
    { id: 'round-map', label: 'Round map' },
    { id: 'decision-map', label: 'Decision map' },
    { id: 'capacity-console', label: 'Capacity console' },
    { id: 'checklists', label: 'Checklists' },
    { id: 'guide-pages', label: 'Drill pages' },
  ];

  return (
    <div className="h-full flex flex-col min-h-0">
      <AppHeader eyebrow="System Design · War Room" title={guide.title} description={guide.description} />
      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto px-5 sm:px-8 pb-8 pt-6">
        <GuideRightRailLayout scrollRef={scrollRef} sectionItems={sectionItems}>
          <GuideCommandStrip
            id="war-room"
            eyebrow="Live round command center"
            description="Ask the right opening questions, run the rough math, pick components only when a pressure demands them, then close with failure modes and trade-offs."
            primaryLabel="Practice prompts"
            config={config}
            guidePages={guidePages}
            stats={[
              { label: 'Round map', value: '45m', icon: Clock3 },
              { label: 'Decision boards', value: guide.sections.length, icon: GitBranch },
              { label: 'Checklist sets', value: guide.checklists.length, icon: ListChecks },
            ]}
          />

          <section id="round-map" className="grid gap-4">
            <WarHeading eyebrow="Timeline" title="Run the interview like a sequence, not a brainstorm" description={opening?.summary} />
            <TimelineCards steps={timeline} />
          </section>

          <section id="decision-map" className="grid gap-4">
            <WarHeading eyebrow="Decision Map" title="Add boxes only when a requirement forces them" description={designOrder?.summary} />
            <DecisionLaneGrid lanes={decisionLanes} />
            {designOrder && (
              <div style={{ ...warCardStyle, padding: 22 }}>
                <div className="mono" style={{ color: 'var(--text-4)', fontSize: 11, letterSpacing: '0.14em' }}>DRAWING ORDER</div>
                <WarActionList items={designOrder.items} />
              </div>
            )}
          </section>

          <section id="capacity-console" className="grid gap-4">
            <WarHeading eyebrow="Capacity Console" title="Turn product scale into architecture pressure" description={capacity?.summary} />
            <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              {(capacity?.items ?? []).map((item, index) => <FormulaCard key={item} item={item} index={index} />)}
            </div>
          </section>

          <section className="grid gap-4">
            <WarHeading eyebrow="Board Cards" title="Followable prompts for the first architecture pass" />
            <div className="grid gap-4 lg:grid-cols-3">
              {guide.sections.map((section, index) => (
                <article key={section.id} id={section.id} style={{ ...warCardStyle, padding: 20, scrollMarginTop: 24 }}>
                  <div className="mono" style={{ color: 'var(--accent)', fontSize: 10.5, letterSpacing: '0.12em' }}>BOARD {String(index + 1).padStart(2, '0')}</div>
                  <h3 className="display-italic" style={{ margin: '10px 0 0', fontSize: 28, lineHeight: 1, fontWeight: 400 }}>{section.title}</h3>
                  <p style={{ margin: '10px 0 14px', color: 'var(--text-3)', fontSize: 13.5, lineHeight: 1.5 }}>{section.summary}</p>
                  <WarActionList items={section.items.slice(0, 5)} compact />
                </article>
              ))}
            </div>
          </section>

          <section id="checklists" className="grid gap-4">
            <WarHeading eyebrow="Pre-flight" title="Scan these before you start speaking" />
            <div className="grid gap-3 lg:grid-cols-2">
              {guide.checklists.map((checklist) => <ChecklistChips key={checklist.title} checklist={checklist} />)}
            </div>
          </section>

          <section id="guide-pages" className="grid gap-4">
            <WarHeading eyebrow="Next Drills" title="Open a focused guide when one decision needs practice" />
            <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              {guidePages.map((resource) => <GuidePageCard key={resource.slug} resource={resource} guidePath={config.guidePath} />)}
            </div>
          </section>
        </GuideRightRailLayout>
      </div>
    </div>
  );
}

export default function SystemDesignGuideExperience({ guide, config, slug, scrollRef }: { guide: GuideRecord; config: GuideConfig; slug?: string; scrollRef: RefObject<HTMLDivElement> }) {
  if (!slug) return <SystemDesignOverview guide={guide} config={config} scrollRef={scrollRef} />;

  const sectionItems: SectionNavItem[] = [
    ...guide.sections.map((section) => ({ id: section.id, label: section.title })),
    { id: 'checklists', label: 'Checklists' },
  ];

  return (
    <PracticeFocusedPage
      guide={guide}
      config={config}
      scrollRef={scrollRef}
      sectionItems={sectionItems}
      eyebrow="System Design · Tactical Brief"
      ctaText="Return to the full war room when you need another decision map."
    />
  );
}
