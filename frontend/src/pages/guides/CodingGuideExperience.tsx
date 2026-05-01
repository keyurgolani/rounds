import type { RefObject } from 'react';
import { Brain, CheckCircle2, Clock3, Code2, Layers3, Route, SearchCheck } from 'lucide-react';
import AppHeader from '../../components/shell/AppHeader';
import type { SectionNavItem } from '../../components/shell/SectionNav';
import type { GuideConfig, GuideRecord } from './guideTypes';
import {
  ChecklistChips,
  DecisionLaneGrid,
  getGuidePages,
  getSection,
  GuidePageCard,
  GuideRightRailLayout,
  GuideCommandStrip,
  LabelDetailCards,
  PracticeFocusedPage,
  SignalCards,
  TimelineCards,
  WarActionList,
  WarHeading,
  warCardStyle,
} from './GuideShared';

const codingTimeline = [
  { time: '0:00', label: 'Restate', detail: 'Input, output, example, and success target.' },
  { time: '0:45', label: 'Clarify', detail: 'Constraints, duplicates, sortedness, mutation, ties, empty input.' },
  { time: '1:30', label: 'Baseline', detail: 'Say brute force and name the bottleneck.' },
  { time: '3:30', label: 'Pattern', detail: 'Map wording to data structure, invariant, and complexity.' },
  { time: '5:00', label: 'Code', detail: 'Only after the interviewer agrees with the plan.' },
  { time: '8:00', label: 'Debug', detail: 'Trace sample, edge case, bug sweep, final complexity.' },
];

const codingDecisionLanes = [
  { title: 'Repeated Lookup', signal: 'Nested membership, pair search, frequency, anagram, first unique', move: 'Reach for hash map/set. Say what the key and stored value are before coding.', icon: SearchCheck },
  { title: 'Moving Boundary', signal: 'Sorted input, longest/shortest window, partition, remove duplicates', move: 'Name the pointer/window invariant and when each boundary moves.', icon: Route },
  { title: 'Priority Or Order', signal: 'Top k, running median, scheduling, next greater, histogram', move: 'Choose heap or monotonic stack. State what leaves the structure and why.', icon: Layers3 },
  { title: 'State Explosion', signal: 'Count ways, min/max choice, overlapping subproblems, all combinations', move: 'Define state, transition, base case, and memo key before implementation.', icon: Brain },
];

const codingRubric = [
  { title: 'Communication', detail: 'Clarify, discuss trade-offs, narrate intent, and avoid silent coding.' },
  { title: 'Problem Solving', detail: 'Baseline, bottleneck, optimized approach, invariant, and complexity.' },
  { title: 'Technical', detail: 'Clean working code, language fluency, small helpers only when useful.' },
  { title: 'Testing', detail: 'Normal case, edge case, bug sweep, self-correction, final complexity.' },
];

export default function CodingGuideExperience({ guide, config, slug, scrollRef }: { guide: GuideRecord; config: GuideConfig; slug?: string; scrollRef: RefObject<HTMLDivElement> }) {
  const guidePages = getGuidePages(guide);
  const roundScript = getSection(guide, 'round-script');
  const patterns = getSection(guide, 'pattern-triggers');
  const complexity = getSection(guide, 'complexity-targets');

  if (slug) {
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
        eyebrow="Coding · Drill Brief"
        ctaText="Return to the cockpit when you need the full solve loop, trigger map, and bug sweep."
      />
    );
  }

  const sectionItems: SectionNavItem[] = [
    { id: 'coding-cockpit', label: 'Cockpit' },
    { id: 'solve-loop', label: 'Solve loop' },
    { id: 'pattern-map', label: 'Pattern map' },
    { id: 'complexity', label: 'Complexity' },
    { id: 'optimization', label: 'Optimization' },
    { id: 'checklists', label: 'Checklists' },
    { id: 'guide-pages', label: 'Drill pages' },
  ];

  return (
    <div className="h-full flex flex-col min-h-0">
      <AppHeader eyebrow="Coding · Cockpit" title={guide.title} description={guide.description} />
      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto px-5 sm:px-8 pb-8 pt-6">
        <GuideRightRailLayout scrollRef={scrollRef} sectionItems={sectionItems}>
          <GuideCommandStrip
            id="coding-cockpit"
            eyebrow="Live Coding Cockpit"
            description="Use this as the control panel beside a timed problem: clarify the input, reject slow approaches, name the invariant, code with intent, and test before you say done."
            primaryLabel="Practice problems"
            config={config}
            guidePages={guidePages}
            stats={[
              { label: 'Solve loop', value: '10m', icon: Clock3 },
              { label: 'Pattern triggers', value: patterns?.items.length ?? 0, icon: Code2 },
              { label: 'Rubric signals', value: codingRubric.length, icon: CheckCircle2 },
            ]}
          />

          <section id="solve-loop" className="grid gap-4">
            <WarHeading eyebrow="Operating Script" title="Move through the problem in a predictable order" description={roundScript?.summary} />
            <TimelineCards steps={codingTimeline} />
            {roundScript && <div style={{ ...warCardStyle, padding: 22 }}><WarActionList items={roundScript.items} /></div>}
          </section>

          <section id="pattern-map" className="grid gap-4">
            <WarHeading eyebrow="Pattern Trigger Map" title="Translate prompt wording into a technique" description={patterns?.summary} />
            <SignalCards section={patterns} prefix="TRIGGER" />
          </section>

          <section id="complexity" className="grid gap-4">
            <WarHeading eyebrow="Complexity Guardrails" title="Use constraints to reject bad plans before coding" description={complexity?.summary} />
            <LabelDetailCards section={complexity} prefix="BOUND" />
          </section>

          <section id="optimization" className="grid gap-4">
            <WarHeading eyebrow="Decision Framework" title="Optimize the bottleneck, then prove the code" />
            <DecisionLaneGrid lanes={codingDecisionLanes} />
            <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))' }}>
              {codingRubric.map((item, index) => (
                <article key={item.title} style={{ ...warCardStyle, padding: 18 }}>
                  <div className="mono" style={{ color: 'var(--accent)', fontSize: 10.5, letterSpacing: '0.12em' }}>SIGNAL {String(index + 1).padStart(2, '0')}</div>
                  <h3 style={{ margin: '12px 0 0', fontSize: 17 }}>{item.title}</h3>
                  <p style={{ margin: '8px 0 0', color: 'var(--text-3)', fontSize: 13, lineHeight: 1.5 }}>{item.detail}</p>
                </article>
              ))}
            </div>
          </section>

          <section id="checklists" className="grid gap-4">
            <WarHeading eyebrow="Pre-submit Sweep" title="Do this before saying the solution is complete" />
            <div className="grid gap-3 lg:grid-cols-2">
              {guide.checklists.map((checklist) => <ChecklistChips key={checklist.title} checklist={checklist} />)}
            </div>
          </section>

          <section id="guide-pages" className="grid gap-4">
            <WarHeading eyebrow="Next Drills" title="Open the focused page for the skill that broke down" />
            <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              {guidePages.map((resource) => <GuidePageCard key={resource.slug} resource={resource} guidePath={config.guidePath} />)}
            </div>
          </section>
        </GuideRightRailLayout>
      </div>
    </div>
  );
}
