import type { RefObject } from 'react';
import type { GuideNavGroup } from '../shared/GuideNav';
import type { TrackConfig } from '../guideTypes';
import StudyShell from '../shared/StudyShell';
import { Section, Pact, ChipRow, LaneCard } from '../shared/primitives';
import { aiCodingContent } from '../content/aiCoding';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function AICodingDashboard({ config, navGroups, scrollRef }: Props) {
  const { dashboard } = aiCodingContent;
  return (
    <StudyShell
      eyebrow={config.eyebrow}
      title={dashboard.title}
      description={dashboard.description}
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Flavors" title="Five flavors of AI coding rounds">
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--gap-md)' }}
        >
          {dashboard.flavorMatrix.map((card) => (
            <LaneCard
              key={card.id}
              eyebrow={card.label}
              title={card.tests}
              body={<span><strong style={{ color: 'var(--text-2)' }}>Move:</strong> {card.dominantMove}</span>}
              footer={<span><strong style={{ color: 'var(--text-3)' }}>Trap:</strong> {card.trap}</span>}
            />
          ))}
        </div>
      </Section>

      <Section eyebrow="Pact" title="What this round actually tests">
        <Pact>{dashboard.whatThisTests}</Pact>
      </Section>

      <Section eyebrow="Companies" title="Where you see it">
        <ChipRow chips={dashboard.companies} />
      </Section>

      <Section eyebrow="Time" title="Typical time budget">
        <ChipRow chips={[dashboard.timeBudget]} />
      </Section>
    </StudyShell>
  );
}
