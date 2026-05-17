import type { RefObject } from 'react';
import type { GuideNavGroup } from '../shared/GuideNav';
import type { TrackConfig } from '../guideTypes';
import StudyShell from '../shared/StudyShell';
import TimelineStrip, { type TimelinePhase } from '../shared/visuals/TimelineStrip';
import { Section, Pact, Prose } from '../shared/primitives';
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
      <Section
        eyebrow="Round Script"
        title="Eight phases of a live coding round"
        lede="Every successful live-coding interview follows the same rhythm: clarify, frame the invariant, choose the data structure, code, and verify. Skipping phases is the most common reason a correct solution gets scored poorly — the interviewer can't follow your thinking."
      >
        <TimelineStrip phases={phases} />
      </Section>

      <Section
        eyebrow="Pattern Radar"
        title="What pressure → what data structure"
        lede="The words in a problem statement almost always telegraph which data structure belongs. Read these signal phrases and let them pull you toward the right tool before you start coding."
      >
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

      <Section
        title="Code style pact"
        lede="Interviewers evaluate clarity as much as correctness. These style rules exist so your code communicates intent at a glance — descriptive names and tight loops are faster to debug together than terse one-liners."
      >
        <Pact>{dashboard.codeStylePact}</Pact>
      </Section>
    </StudyShell>
  );
}
