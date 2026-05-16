import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, ThesisLine, LaneCard, ChipRow } from '../../shared/primitives';
import InfographicFrame from '../../shared/visuals/InfographicFrame';
import { codingContent } from '../../content/coding';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function MentalModel({ config, navGroups, scrollRef }: Props) {
  const { mentalModel } = codingContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Mental Model`}
      title="Coding Mental Model"
      description="The small set of rules that decides what to code next."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Thesis" title="Invariant first">
        <ThesisLine>{mentalModel.thesis}</ThesisLine>
      </Section>

      <Section eyebrow="Invariant Loop" title="The four-step cycle every solve runs through">
        <InfographicFrame caption="Loop">
          <InvariantLoop />
        </InfographicFrame>
      </Section>

      <Section eyebrow="State" title="What 'name the state' looks like">
        <div
          className="grid"
          style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}
        >
          {mentalModel.stateExamples.map((entry) => (
            <LaneCard
              key={entry.pattern}
              eyebrow={entry.pattern}
              title={entry.state}
            />
          ))}
        </div>
      </Section>

      <Section eyebrow="Stress Tests" title="Edge cases the invariant should survive">
        <ChipRow chips={mentalModel.edgeCases} />
      </Section>
    </StudyShell>
  );
}

function InvariantLoop() {
  // Static SVG cycle: State → Invariant → Action → Proof → State.
  const labels = ['State', 'Invariant', 'Action', 'Proof'];
  const radius = 110;
  const center = { x: 200, y: 130 };
  return (
    <svg viewBox="0 0 400 260" width="100%" style={{ maxWidth: 480 }} aria-hidden="true">
      <defs>
        <marker id="loop-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="var(--text-4)" />
        </marker>
      </defs>
      {labels.map((label, index) => {
        const angle = (-Math.PI / 2) + (index * Math.PI / 2);
        const x = center.x + radius * Math.cos(angle);
        const y = center.y + radius * Math.sin(angle);
        return (
          <g key={label} transform={`translate(${x},${y})`}>
            <circle r={36} fill="var(--accent-soft)" stroke="var(--accent)" strokeWidth={1.5} />
            <text textAnchor="middle" dy="0.35em" fontSize={13} fontWeight={600} fill="var(--accent)">
              {label}
            </text>
          </g>
        );
      })}
      {/* arrows clockwise */}
      {labels.map((_, index) => {
        const startAngle = (-Math.PI / 2) + (index * Math.PI / 2);
        const endAngle = startAngle + Math.PI / 2;
        const inset = 38;
        const startX = center.x + (radius - inset) * Math.cos(startAngle + 0.32);
        const startY = center.y + (radius - inset) * Math.sin(startAngle + 0.32);
        const endX = center.x + (radius - inset) * Math.cos(endAngle - 0.32);
        const endY = center.y + (radius - inset) * Math.sin(endAngle - 0.32);
        return (
          <path
            key={`arc-${index}`}
            d={`M ${startX} ${startY} A ${radius - inset} ${radius - inset} 0 0 1 ${endX} ${endY}`}
            fill="none"
            stroke="var(--text-4)"
            strokeWidth={1.5}
            markerEnd="url(#loop-arrow)"
          />
        );
      })}
    </svg>
  );
}
