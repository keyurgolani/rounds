import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import {
  Section,
  Callout,
  KeyValueRow,
  GuidanceGrid,
  Guidance,
  SubHeading,
} from '../../shared/primitives';
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
      <Section
        title="The take-home trade-off triangle"
        lede="Every take-home forces you to balance three things: how much you build (scope), how well you build it (quality), and how long you spend (time). You cannot pull on one corner without the other two shifting. Knowing which corner to sacrifice — and saying so in your README — is itself a signal of senior judgment."
      >
        <Callout>{mentalModel.thesis}</Callout>
        <InfographicFrame caption="Scope · Quality · Time">
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

      <Section
        title={'What "ship" actually means'}
        lede="In a take-home context, 'shipped' is not the same as 'coded.' Something is shipped when a reviewer can clone it, run it, and understand it in under 5 minutes without your help. These four criteria define the bar — not lines of code, not cleverness."
      >
        <GuidanceGrid>
          {mentalModel.shipMeans.map((item, i) => (
            <Guidance key={i} label={`Criterion ${i + 1}`}>
              {item}
            </Guidance>
          ))}
        </GuidanceGrid>
      </Section>

      <Section
        title="What to cut without regret"
        lede="Take-homes punish over-scope. When you are running short on time, these are the safe cuts — things that feel important in the moment but rarely change a reviewer's evaluation. Name every cut in the README so reviewers know you made a deliberate choice, not an oversight."
      >
        <SubHeading>Safe cuts</SubHeading>
        <GuidanceGrid>
          {mentalModel.whatToCut.map((item, i) => (
            <Guidance key={i} label="">
              {item}
            </Guidance>
          ))}
        </GuidanceGrid>
      </Section>
    </StudyShell>
  );
}
