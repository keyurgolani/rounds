import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig, BuilderFlavor } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import {
  Section,
  Callout,
  LaneCard,
  GuidanceGrid,
  Guidance,
} from '../../shared/primitives';
import DecisionDeck from '../../shared/visuals/DecisionDeck';
import { builderContent } from '../../content/builder';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

function prettyLabel(id: BuilderFlavor): string {
  const map: Record<BuilderFlavor, string> = {
    'services-apis':       'Services / APIs',
    'data-etl':            'Data / ETL',
    'concurrency-systems': 'Concurrency / Systems',
    'domain-modeled':      'Domain-modeled',
  };
  return map[id] ?? id;
}

export default function Cheatsheet({ config, navGroups, scrollRef }: Props) {
  const { cheatsheet } = builderContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Cheatsheet`}
      title="Builder Cheatsheet"
      description="Day budget, flavor move, AI policy — at a glance."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        eyebrow="Time"
        title="What is reasonable to ship at each day budget"
        lede="These are the realistic quality bars for each time budget — not aspirational targets. Hitting the bar for your budget cleanly beats overreaching and leaving gaps. Use the round-length picker to set your budget before reviewing the Time Plan page."
      >
        <div
          className="flex"
          style={{ gap: 'var(--gap-sm)', overflowX: 'auto', paddingBottom: 6 }}
        >
          {cheatsheet.timeTiers.map((entry) => (
            <div
              key={entry.tier}
              className="card"
              style={{
                minWidth: 220,
                padding: 'var(--pad-sm)',
                display: 'grid',
                gap: 6,
              }}
            >
              <span
                className="mono"
                style={{ fontSize: 11, color: 'var(--text-4)', letterSpacing: '0.12em' }}
              >
                {entry.tier.toUpperCase()}
              </span>
              <span style={{ color: 'var(--text-2)', fontSize: 13, lineHeight: 1.5 }}>
                {entry.reasonable}
              </span>
            </div>
          ))}
        </div>
      </Section>

      <Section
        eyebrow="Flavors"
        title="Pick the right move for the flavor"
        lede="The prompt's domain tells you what the opening move should be. Getting the move right in the first few hours sets the direction for the rest of the take-home — getting it wrong means refactoring under time pressure later."
      >
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

      <Section
        eyebrow="AI Policy"
        title="How to behave under each policy"
        lede="The prompt's AI policy changes what you put in the README, not necessarily how much help you get. Even under a strict 'off' policy, you can read documentation, search for examples, and reference open-source code — the line is code generation, not all external resources."
      >
        <Callout>
          Under any policy: own every line. The follow-up call will test whether you understand
          what you submitted.
        </Callout>
        <GuidanceGrid>
          {cheatsheet.aiPolicyMoves.map((policy) => (
            <Guidance key={policy.policy} label={policy.policy.toUpperCase()}>
              {policy.behave}
            </Guidance>
          ))}
        </GuidanceGrid>
      </Section>
    </StudyShell>
  );
}
