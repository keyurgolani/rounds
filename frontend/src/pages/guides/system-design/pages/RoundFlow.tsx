import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Pact } from '../../shared/primitives';
import TimelineStrip, { type TimelinePhase } from '../../shared/visuals/TimelineStrip';
import { systemDesignContent } from '../../content/systemDesign';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function RoundFlow({ config, navGroups, scrollRef }: Props) {
  const { roundFlow } = systemDesignContent;
  const phases: TimelinePhase[] = roundFlow.phases.map((phase) => ({
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
      eyebrow={`${config.eyebrow} · Round Flow`}
      title="45-minute Round Flow"
      description="Hello Interview's delivery framework: six phases, six checklists, six minute-budgets."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Timeline" title="Six phases, minute by minute">
        <TimelineStrip phases={phases} />
      </Section>

      <Section eyebrow="Phrases" title="Useful lines for the round">
        <Pact>
          <ol style={{ margin: 0, paddingLeft: 18 }}>
            {roundFlow.usefulPhrases.map((line) => (
              <li key={line} style={{ marginBottom: 8 }}>{line}</li>
            ))}
          </ol>
        </Pact>
      </Section>
    </StudyShell>
  );
}
