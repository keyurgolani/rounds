import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig, BuilderFlavor } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, LaneCard } from '../../shared/primitives';
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
      description="Time tier, flavor move, AI policy — at a glance."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Time" title="What's reasonable to ship at each budget">
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

      <Section eyebrow="AI Policy" title="How to behave under each policy">
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 'var(--gap-md)' }}
        >
          {cheatsheet.aiPolicyMoves.map((policy) => (
            <LaneCard
              key={policy.policy}
              eyebrow={policy.policy.toUpperCase()}
              title={policy.behave}
            />
          ))}
        </div>
      </Section>
    </StudyShell>
  );
}
