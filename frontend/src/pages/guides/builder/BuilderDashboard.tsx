import type { RefObject } from 'react';
import type { GuideNavGroup } from '../shared/GuideNav';
import type { TrackConfig } from '../guideTypes';
import StudyShell from '../shared/StudyShell';
import { Section, Pact, ChipRow, LaneCard } from '../shared/primitives';
import { builderContent } from '../content/builder';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function BuilderDashboard({ config, navGroups, scrollRef }: Props) {
  const { dashboard } = builderContent;
  const policySegments = [
    { label: 'off',              count: dashboard.policyDistribution.off,    active: false },
    { label: 'candidate-choice', count: dashboard.policyDistribution.choice, active: false },
    { label: 'on',               count: dashboard.policyDistribution.on,     active: true },
  ];

  return (
    <StudyShell
      eyebrow={config.eyebrow}
      title={dashboard.title}
      description={dashboard.description}
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Flavors" title="Four flavors of real-world problems">
        <div
          className="grid"
          style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
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

      <Section eyebrow="AI Policy" title="Distribution across the 20 briefs">
        <div className="card" style={{ padding: 'var(--pad-md)', display: 'grid', gap: 'var(--gap-sm)' }}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '2fr 6fr 12fr',
              gap: 4,
              overflow: 'hidden',
              borderRadius: 'var(--radius)',
            }}
          >
            {policySegments.map((seg) => (
              <div
                key={seg.label}
                style={{
                  padding: '10px 12px',
                  background: seg.active ? 'var(--accent)' : 'var(--accent-soft)',
                  color: seg.active ? 'var(--bg-elev)' : 'var(--accent)',
                  fontSize: 12.5,
                  fontWeight: 600,
                  textAlign: 'center',
                }}
              >
                {seg.label} · {seg.count}
              </div>
            ))}
          </div>
        </div>
      </Section>

      <Section eyebrow="Time" title="The six time tiers">
        <ChipRow chips={dashboard.timeTiers} />
      </Section>

      <Section eyebrow="Pact" title="What 'submitted' means">
        <Pact>{dashboard.submissionPact}</Pact>
      </Section>
    </StudyShell>
  );
}
