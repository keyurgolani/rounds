import type { RefObject } from 'react';
import { Gauge, MessageSquare, Sparkles, Target, Users } from 'lucide-react';
import AppHeader from '../../components/shell/AppHeader';
import type { SectionNavItem } from '../../components/shell/SectionNav';
import type { GuideConfig, GuideRecord } from './guideTypes';
import {
  ChecklistChips,
  DecisionLaneGrid,
  getGuidePages,
  getSection,
  GuideCommandStrip,
  GuidePageCard,
  GuideRightRailLayout,
  LabelDetailCards,
  PracticeFocusedPage,
  SignalCards,
  TimelineCards,
  WarActionList,
  WarHeading,
  warCardStyle,
} from './GuideShared';

const behavioralStar = [
  { label: 'Situation', time: '15s', detail: 'Project, stakes, constraint.' },
  { label: 'Task', time: '10s', detail: 'Your responsibility and success target.' },
  { label: 'Action', time: '60-90s', detail: 'Decisions, trade-offs, communication, execution.' },
  { label: 'Result', time: '15-25s', detail: 'Numbers, outcome, secondary effect.' },
  { label: 'Reflection', time: '10-20s', detail: 'Behavior change and later proof.' },
];

const behavioralSignalLanes = [
  { title: 'Ownership', signal: 'Problem was under-owned, ambiguous, risky, or outside your lane', move: 'Show what you noticed, the plan you created, and how you drove follow-through.', icon: Target },
  { title: 'Influence', signal: 'Conflict, disagreement, cross-functional work, stakeholder tension', move: 'Represent both sides fairly, name decision criteria, and show changed behavior.', icon: Users },
  { title: 'Growth', signal: 'Failure, feedback, weakness, missed expectation, later correction', move: 'Own your part, quantify repair, and prove the future behavior changed.', icon: Sparkles },
  { title: 'Scope', signal: 'Senior loop, level calibration, staff/principal expectations', move: 'Name teams, users, revenue, systems, risk, timeline, and operating mechanism.', icon: Gauge },
];

export default function BehavioralGuideExperience({ guide, config, slug, scrollRef }: { guide: GuideRecord; config: GuideConfig; slug?: string; scrollRef: RefObject<HTMLDivElement> }) {
  const guidePages = getGuidePages(guide);
  const storyBank = getSection(guide, 'story-bank');
  const answerShape = getSection(guide, 'answer-shape');
  const signalMap = getSection(guide, 'signal-map');

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
        eyebrow="Behavioral · Practice Brief"
        ctaText="Return to the story lab when you need the portfolio board, signal map, and repair checklist."
      />
    );
  }

  const sectionItems: SectionNavItem[] = [
    { id: 'story-lab', label: 'Story lab' },
    { id: 'portfolio', label: 'Portfolio' },
    { id: 'answer-shape', label: 'Answer shape' },
    { id: 'signal-map', label: 'Signal map' },
    { id: 'repair-board', label: 'Repair board' },
    { id: 'checklists', label: 'Checklists' },
    { id: 'guide-pages', label: 'Drill pages' },
  ];

  return (
    <div className="h-full flex flex-col min-h-0">
      <AppHeader eyebrow="Behavioral · Story Lab" title={guide.title} description={guide.description} />
      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto px-5 sm:px-8 pb-8 pt-6">
        <GuideRightRailLayout scrollRef={scrollRef} sectionItems={sectionItems}>
          <GuideCommandStrip
            id="story-lab"
            eyebrow="Behavioral Story Lab"
            description="Use this page to build reusable stories, keep answers under control, attach every trait to evidence, and close weak interpretations before the interviewer does."
            primaryLabel="Practice questions"
            config={config}
            guidePages={guidePages}
            stats={[
              { label: 'Story bank', value: storyBank?.items.length ?? 0, icon: Users },
              { label: 'Answer shape', value: 'STAR(R)', icon: MessageSquare },
              { label: 'Signal lanes', value: behavioralSignalLanes.length, icon: Target },
            ]}
          />

          <section id="portfolio" className="grid gap-4">
            <WarHeading eyebrow="Story Portfolio" title="Cover the eight stories before any loop" description={storyBank?.summary} />
            <LabelDetailCards section={storyBank} prefix="STORY" />
          </section>

          <section id="answer-shape" className="grid gap-4">
            <WarHeading eyebrow="Answer Shape" title="Use time boxes so the story does not sprawl" description={answerShape?.summary} />
            <TimelineCards steps={behavioralStar.map((step) => ({ time: step.time, label: step.label, detail: step.detail }))} />
            {answerShape && <div style={{ ...warCardStyle, padding: 22 }}><WarActionList items={answerShape.items} /></div>}
          </section>

          <section id="signal-map" className="grid gap-4">
            <WarHeading eyebrow="Signal Map" title="Do not claim traits. Attach each one to proof" description={signalMap?.summary} />
            <SignalCards section={signalMap} prefix="SIGNAL" />
          </section>

          <section id="repair-board" className="grid gap-4">
            <WarHeading eyebrow="Decision Framework" title="Frame senior stories defensively before follow-ups" />
            <DecisionLaneGrid lanes={behavioralSignalLanes} />
          </section>

          <section id="checklists" className="grid gap-4">
            <WarHeading eyebrow="Red Flag Sweep" title="Remove weak signal before the mock starts" />
            <div className="grid gap-3 lg:grid-cols-2">
              {guide.checklists.map((checklist) => <ChecklistChips key={checklist.title} checklist={checklist} />)}
            </div>
          </section>

          <section id="guide-pages" className="grid gap-4">
            <WarHeading eyebrow="Next Drills" title="Open the focused page for the story problem you need to repair" />
            <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              {guidePages.map((resource) => <GuidePageCard key={resource.slug} resource={resource} guidePath={config.guidePath} />)}
            </div>
          </section>
        </GuideRightRailLayout>
      </div>
    </div>
  );
}
