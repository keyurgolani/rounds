import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, ChipRow } from '../../shared/primitives';
import DecisionDeck from '../../shared/visuals/DecisionDeck';
import { systemDesignContent } from '../../content/systemDesign';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function Cheatsheet({ config, navGroups, scrollRef }: Props) {
  const { cheatsheet } = systemDesignContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Cheatsheet`}
      title="System Design Cheatsheet"
      description="Trigger → move → watch. The decision deck you reach for when the interviewer says 'why this component?'"
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Pre-flight" title="Before you draw">
        <ChipRow chips={cheatsheet.preflight} />
      </Section>

      <Section eyebrow="Decision Deck" title="Eight moves that recur in every round">
        <DecisionDeck entries={cheatsheet.decisionDeck} />
      </Section>

      <Section eyebrow="Traps" title="Don't get caught here">
        <ChipRow chips={cheatsheet.traps} />
      </Section>
    </StudyShell>
  );
}
