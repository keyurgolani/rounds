import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, ChipRow, Prose } from '../../shared/primitives';
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
      <Section
        title="Before you draw"
        lede="Spend the first few minutes on the discipline below, not on architecture. Each item is a one-line forcing function that shapes the rest of the round. Skip them and you'll spend the deep-dive backfilling assumptions you should have stated up front."
      >
        <ChipRow chips={cheatsheet.preflight} />
      </Section>

      <Section
        title="Eight moves that recur in every round"
        lede="Most system-design rounds reduce to a small set of recurring decisions. Below is the menu — each card pairs a trigger with the move you should default to, and the trap it leaves behind. When the interviewer asks 'why this component?', the answer should come from one of these cards."
      >
        <DecisionDeck entries={cheatsheet.decisionDeck} />
      </Section>

      <Section
        title="Don't get caught here"
        lede="These are the failure modes that turn an otherwise solid design into a 'didn't think hard enough about scale' debrief. Run through them in the final two minutes before you summarise."
      >
        <ChipRow chips={cheatsheet.traps} />
        <Prose>
          Each trap is the absence of a constraint you didn't name. The fix is
          almost always to surface the constraint, not to add another component
          on top.
        </Prose>
      </Section>
    </StudyShell>
  );
}
