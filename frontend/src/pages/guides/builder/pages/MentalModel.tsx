import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, ThesisLine, KeyValueRow, LaneCard, ChipRow } from '../../shared/primitives';
import InfographicFrame from '../../shared/visuals/InfographicFrame';
import { builderContent } from '../../content/builder';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

const TRIANGLE_CORNERS = [
  { x: 180, y: 30,  label: 'Scope' },
  { x: 30,  y: 250, label: 'Quality' },
  { x: 330, y: 250, label: 'Time' },
] as const;

export default function MentalModel({ config, navGroups, scrollRef }: Props) {
  const { mentalModel } = builderContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Mental Model`}
      title="Builder Mental Model"
      description="Ship small. Prove early. Document what you cut."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Thesis" title="Pull on one corner; the other two move.">
        <ThesisLine>{mentalModel.thesis}</ThesisLine>
      </Section>

      <Section eyebrow="Triangle" title="The take-home trade-off">
        <InfographicFrame caption="Triangle">
          <div
            className="grid"
            style={{ gap: 'var(--gap-md)', width: '100%', justifyItems: 'center' }}
          >
            <svg
              viewBox="0 0 360 280"
              width="100%"
              style={{ maxWidth: 420 }}
              aria-hidden="true"
            >
              <polygon
                points="180,30 30,250 330,250"
                fill="none"
                stroke="var(--border-strong)"
                strokeWidth={1.5}
              />
              {TRIANGLE_CORNERS.map((corner) => (
                <g key={corner.label} transform={`translate(${corner.x},${corner.y})`}>
                  <circle r={38} fill="var(--accent-soft)" stroke="var(--accent)" strokeWidth={1.5} />
                  <text
                    textAnchor="middle"
                    dy="0.35em"
                    fontSize={13}
                    fontWeight={600}
                    fill="var(--accent)"
                  >
                    {corner.label}
                  </text>
                </g>
              ))}
            </svg>
          </div>
        </InfographicFrame>
        <div className="grid" style={{ gap: 0 }}>
          {mentalModel.triageTriangle.map((corner) => (
            <KeyValueRow key={corner.corner} label={corner.corner} value={corner.meaning} />
          ))}
        </div>
      </Section>

      <Section eyebrow="Ship" title={'What "ship" actually means'}>
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--gap-md)' }}
        >
          {mentalModel.shipMeans.map((item) => (
            <LaneCard key={item} title={item} />
          ))}
        </div>
      </Section>

      <Section eyebrow="Cut" title="What to cut without regret">
        <ChipRow chips={mentalModel.whatToCut} />
      </Section>
    </StudyShell>
  );
}
