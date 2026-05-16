import type { RefObject } from 'react';
import type { GuideNavGroup } from '../shared/GuideNav';
import type { TrackConfig } from '../guideTypes';
import StudyShell from '../shared/StudyShell';
import TimelineStrip, { type TimelinePhase } from '../shared/visuals/TimelineStrip';
import { Section, Pact } from '../shared/primitives';
import { Link } from 'react-router-dom';
import { codingContent } from '../content/coding';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function CodingDashboard({ config, navGroups, scrollRef }: Props) {
  const { dashboard } = codingContent;
  const phases: TimelinePhase[] = dashboard.roundPhases.map((phase) => ({
    id: phase.id,
    label: phase.label,
    caption: 'Phase',
    body: (
      <div className="grid" style={{ gap: 4 }}>
        <span><strong style={{ color: 'var(--text-2)' }}>Say:</strong> {phase.say}</span>
        <span><strong style={{ color: 'var(--text-2)' }}>Write:</strong> {phase.write}</span>
      </div>
    ),
  }));

  return (
    <StudyShell
      eyebrow={config.eyebrow}
      title={dashboard.title}
      description={dashboard.description}
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Round Script" title="Eight phases of a live coding round">
        <TimelineStrip phases={phases} />
      </Section>

      <Section eyebrow="Pattern Radar" title="What pressure → what data structure">
        <div
          className="grid"
          style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
        >
          {dashboard.patternRadar.map((entry) => (
            <Link
              key={entry.id}
              to={`${config.guidePath}/${entry.topicSlug}`}
              className="card card-hover"
              style={{
                display: 'grid',
                gap: 6,
                padding: 'var(--pad-md)',
                textDecoration: 'none',
                color: 'var(--text)',
              }}
            >
              <span className="eyebrow">When you see</span>
              <strong style={{ fontSize: 14, fontWeight: 600 }}>{entry.name}</strong>
              <span style={{ color: 'var(--text-3)', fontSize: 12.5, lineHeight: 1.45 }}>{entry.trigger}</span>
            </Link>
          ))}
        </div>
      </Section>

      <Section eyebrow="Style" title="Code style pact">
        <Pact>{dashboard.codeStylePact}</Pact>
      </Section>
    </StudyShell>
  );
}
