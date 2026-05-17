import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Callout, Pact, LaneCard, Prose } from '../../shared/primitives';
import InfographicFrame from '../../shared/visuals/InfographicFrame';
import { systemDesignContent } from '../../content/systemDesign';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

const FORCES = [
  { id: 'users',       label: 'Users' },
  { id: 'scale',       label: 'Scale' },
  { id: 'latency',     label: 'Latency' },
  { id: 'consistency', label: 'Consistency' },
  { id: 'reliability', label: 'Reliability' },
  { id: 'retention',   label: 'Retention' },
];

const COMPONENTS = [
  { id: 'cache',        label: 'Cache' },
  { id: 'queue',        label: 'Queue' },
  { id: 'sharding',     label: 'Sharding' },
  { id: 'cdn',          label: 'CDN' },
  { id: 'consensus',    label: 'Consensus' },
  { id: 'replication',  label: 'Replication' },
  { id: 'multi-region', label: 'Multi-region' },
  { id: 'cold-storage', label: 'Cold storage' },
];

export default function MentalModel({ config, navGroups, scrollRef }: Props) {
  const { mentalModel } = systemDesignContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Mental Model`}
      title="System Design Mental Model"
      description="The lens that turns vague prompts into architecture choices."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        title="Pressure before components"
        lede="A system design prompt rarely tells you which component to draw — it tells you what the system must endure. Reading the requirements is the act of naming each force the system is under (users, latency, retention, consistency). Components come second; they exist only to absorb a specific force."
      >
        <Callout>{mentalModel.thesis}</Callout>
      </Section>

      <Section
        title="Forces → architecture"
        lede="Each force in your requirements pulls in a small set of components. The diagram below maps the recurring force-to-component edges that show up in interviews. When you draw a component, you should be able to trace it back to one of these forces."
      >
        <InfographicFrame caption="Each line is one force that earns one component its seat">
          <ForcesGraph links={mentalModel.forceComponentLinks} />
        </InfographicFrame>
      </Section>

      <Section
        title="Every box on the board must answer four questions"
        lede="Before you accept any component into your design, run it through these four checks. If you can't answer one cleanly, you're padding the diagram — and an interviewer will hear it."
      >
        <div className="grid" style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
          {mentalModel.earnItsSeatQuestions.map((question, index) => (
            <LaneCard
              key={question}
              eyebrow={`Question ${String(index + 1).padStart(2, '0')}`}
              title={question}
            />
          ))}
        </div>
      </Section>

      <Section
        title="Path before infrastructure"
        lede="The order in which you build the design matters as much as the design itself. Walk one user request end-to-end across the components you've drawn — only then add scaling primitives. This keeps the conversation grounded in behaviour, not architecture astronomy."
      >
        <Pact>{mentalModel.pathBeforeInfraNote}</Pact>
        <Prose>
          A common failure mode is jumping to caches, queues, and shards before the
          single-user path is even traced through the system. Walk one request all
          the way through first; then bring in the scaling primitives the forces
          actually justify.
        </Prose>
      </Section>
    </StudyShell>
  );
}

function ForcesGraph({
  links,
}: {
  links: { force: string; component: string }[];
}) {
  const leftX = 60;
  const rightX = 360;
  const rowHeight = 42;
  const padTop = 18;
  const findY = (items: { id: string }[], id: string) => {
    const idx = items.findIndex((item) => item.id === id);
    return padTop + idx * rowHeight + (rowHeight - 8) / 2;
  };

  const totalHeight = padTop * 2 + Math.max(FORCES.length, COMPONENTS.length) * rowHeight;

  return (
    <svg viewBox={`0 0 500 ${totalHeight}`} width="100%" style={{ maxWidth: 560 }}>
      {FORCES.map((force, index) => (
        <g key={force.id} transform={`translate(${leftX}, ${padTop + index * rowHeight})`}>
          <rect width={140} height={rowHeight - 8} rx={6} fill="var(--accent-soft)" stroke="var(--accent)" strokeWidth={1} />
          <text x={70} y={(rowHeight - 8) / 2 + 4} textAnchor="middle" fontSize={12} fontWeight={600} fill="var(--accent)">
            {force.label}
          </text>
        </g>
      ))}
      {COMPONENTS.map((component, index) => (
        <g key={component.id} transform={`translate(${rightX}, ${padTop + index * rowHeight})`}>
          <rect width={140} height={rowHeight - 8} rx={6} fill="var(--bg-elev)" stroke="var(--border-strong)" strokeWidth={1} />
          <text x={70} y={(rowHeight - 8) / 2 + 4} textAnchor="middle" fontSize={12} fontWeight={500} fill="var(--text-2)">
            {component.label}
          </text>
        </g>
      ))}
      {links.map((link, index) => {
        const startY = findY(FORCES, link.force);
        const endY = findY(COMPONENTS, link.component);
        return (
          <path
            key={`link-${index}`}
            d={`M ${leftX + 140} ${startY} C 280 ${startY}, 280 ${endY}, ${rightX} ${endY}`}
            stroke="var(--text-4)"
            strokeWidth={1.2}
            fill="none"
            opacity={0.7}
          />
        );
      })}
    </svg>
  );
}
