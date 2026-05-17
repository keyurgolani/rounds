import type { RefObject } from 'react';
import type { GuideNavGroup } from '../shared/GuideNav';
import type { TrackConfig } from '../guideTypes';
import StudyShell from '../shared/StudyShell';
import { Section, ChipRow, Prose } from '../shared/primitives';
import TimelineStrip, { type TimelinePhase } from '../shared/visuals/TimelineStrip';
import InfographicFrame from '../shared/visuals/InfographicFrame';
import { systemDesignContent } from '../content/systemDesign';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function SystemDesignDashboard({ config, navGroups, scrollRef }: Props) {
  const { dashboard } = systemDesignContent;
  const phases: TimelinePhase[] = dashboard.timeline.map((phase) => ({
    id: phase.id,
    label: phase.label,
    caption: phase.minutes,
    body: (
      <ul style={{ margin: 0, paddingLeft: 14 }}>
        {phase.checklist.map((item) => (
          <li key={item} style={{ color: 'var(--text-3)', fontSize: 12, lineHeight: 1.45 }}>{item}</li>
        ))}
      </ul>
    ),
  }));

  return (
    <StudyShell
      eyebrow={config.eyebrow}
      title={dashboard.title}
      description={dashboard.description}
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Whiteboard" title="The board layout an interviewer expects to see">
        <InfographicFrame caption={dashboard.boardLayoutCaption}>
          <BoardLayoutSketch />
        </InfographicFrame>
      </Section>

      <Section
        eyebrow="Timeline"
        title="The round, end to end"
        lede="The exact minute split scales with the round length you pick above. Each phase below assumes its share of the total time and adapts as you change the picker."
      >
        <TimelineStrip phases={phases} />
      </Section>

      <Section
        eyebrow="Pressure Menu"
        title="What requirements force into the design"
        lede="Before sketching components, name the forces in the prompt. Each force in the menu below is a wedge that earns a specific component its seat on the board. Skip naming the forces and the architecture turns into a wish list."
      >
        <ChipRow chips={dashboard.pressureMenu} />
        <Prose>
          When you read the requirements, underline the words that map to these
          forces. The mapping is the connective tissue between problem and design —
          and it's also what an interviewer is grading.
        </Prose>
      </Section>
    </StudyShell>
  );
}

function BoardLayoutSketch() {
  // Static SVG sketch — 5 panels mirroring the whiteboard layout.
  const cellStyle = {
    stroke: 'var(--border-strong)',
    fill: 'var(--bg-elev)',
    strokeWidth: 1.4,
  };
  const text = (x: number, y: number, label: string, eyebrow: string) => (
    <g key={label}>
      <text x={x + 10} y={y + 20} fontSize={9} letterSpacing="0.1em" fill="var(--text-4)">{eyebrow.toUpperCase()}</text>
      <text x={x + 10} y={y + 40} fontSize={13} fontWeight={600} fill="var(--text-2)">{label}</text>
    </g>
  );
  return (
    <svg viewBox="0 0 480 280" width="100%" style={{ maxWidth: 540 }} aria-hidden="true">
      <rect x={10}  y={10}  width={210} height={70}  rx={6} {...cellStyle} />
      <rect x={230} y={10}  width={240} height={70}  rx={6} {...cellStyle} />
      <rect x={10}  y={90}  width={460} height={100} rx={6} {...cellStyle} />
      <rect x={10}  y={200} width={210} height={70}  rx={6} {...cellStyle} />
      <rect x={230} y={200} width={240} height={70}  rx={6} {...cellStyle} />
      {text(10,  10,  'Requirements',     'Top-left')}
      {text(230, 10,  'Scale numbers',    'Top-right')}
      {text(10,  90,  'Architecture',     'Middle (read + write paths)')}
      {text(10,  200, 'Data model',       'Bottom-left')}
      {text(230, 200, 'Failure modes',    'Bottom-right')}
    </svg>
  );
}
