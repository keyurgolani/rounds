import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig, AIFlavor } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, LaneCard, ChipRow } from '../../shared/primitives';
import DecisionDeck from '../../shared/visuals/DecisionDeck';
import { aiCodingContent } from '../../content/aiCoding';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

function prettyLabel(id: AIFlavor): string {
  const map: Record<AIFlavor, string> = {
    'audit': 'Audit',
    'drive': 'Drive',
    'debug-refactor': 'Debug-Refactor',
    'prompt-spec': 'Prompt-Spec',
    'mini-app': 'Mini-app',
  };
  return map[id] ?? id;
}

export default function Cheatsheet({ config, navGroups, scrollRef }: Props) {
  const { cheatsheet } = aiCodingContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Cheatsheet`}
      title="AI Coding Cheatsheet"
      description="Policy mode, flavor move, red flag — at a glance."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Policy" title="What the AI policy means">
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--gap-md)' }}
        >
          {cheatsheet.policyModes.map((mode) => (
            <LaneCard
              key={mode.mode}
              eyebrow={mode.mode.toUpperCase()}
              title={mode.when}
              body={`Expectation: ${mode.expectation}`}
            />
          ))}
        </div>
      </Section>

      <Section eyebrow="Flavors" title="Pick the right move for the flavor">
        <DecisionDeck
          entries={cheatsheet.flavorDeck.map((card) => ({
            id: card.id,
            eyebrow: prettyLabel(card.id),
            trigger: card.trigger,
            move: card.move,
            watch: card.watch,
          }))}
        />
      </Section>

      <Section eyebrow="Watch" title="Red-flag pile">
        <ChipRow chips={cheatsheet.redFlags} />
      </Section>
    </StudyShell>
  );
}
