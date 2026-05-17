import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Pact, Prose } from '../../shared/primitives';
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
      title="Round Flow"
      description="Six phases, six checklists, six minute-budgets — paced to the round length you set above."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        title="The six phases, minute by minute"
        lede="A system-design round has a natural shape, and an interviewer is tracking how much time you spend in each phase. The point of pacing isn't to rush — it's to make sure each phase gets its share, because the early phases compound: the requirements you skip in minute 4 become the missing constraints in minute 35."
      >
        <TimelineStrip phases={phases} />
      </Section>

      <Section
        title="Useful lines for the round"
        lede="Memorise these out loud. The phrases below are the connective tissue between your design and the trade-off conversation an interviewer wants. Most candidates have the right intuition but never say it — these lines force you to make the reasoning audible."
      >
        <Pact>
          <ol style={{ margin: 0, paddingLeft: 18 }}>
            {roundFlow.usefulPhrases.map((line) => (
              <li key={line} style={{ marginBottom: 8 }}>{line}</li>
            ))}
          </ol>
        </Pact>
        <Prose size="sm">
          Use one of these phrases at the end of each phase, when you commit to a
          choice. They land best when paired with a specific number — a latency
          budget, an SLO target, a row count.
        </Prose>
      </Section>
    </StudyShell>
  );
}
