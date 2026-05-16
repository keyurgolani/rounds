import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, LaneCard, Pact } from '../../shared/primitives';
import { aiCodingContent } from '../../content/aiCoding';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function ReviewHabits({ config, navGroups, scrollRef }: Props) {
  const { reviewHabits } = aiCodingContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Review Habits`}
      title="Review Habits"
      description="The 5-dimension checklist + common AI defects."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Checklist" title="Review every AI output along five axes">
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 'var(--gap-sm)' }}
        >
          {reviewHabits.checklist.map((item) => (
            <LaneCard key={item.dim} eyebrow={item.dim} title={item.check} />
          ))}
        </div>
      </Section>

      <Section eyebrow="Defects" title="What AI gets wrong, with examples">
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 'var(--gap-md)' }}
        >
          {reviewHabits.defects.map((defect) => (
            <div
              key={defect.id}
              className="card"
              style={{
                padding: 'var(--pad-md)',
                background: 'var(--bg-elev)',
                boxShadow: 'inset 0 0 0 1px var(--border)',
                display: 'grid',
                gap: 'var(--gap-sm)',
              }}
            >
              <div className="eyebrow">{defect.defect}</div>
              <pre
                className="mono"
                style={{
                  margin: 0,
                  padding: 'var(--pad-md)',
                  background: 'var(--bg-sunken)',
                  borderRadius: 'var(--radius)',
                  boxShadow: 'inset 0 0 0 1px var(--border)',
                  color: 'var(--text-2)',
                  fontSize: 12,
                  lineHeight: 1.55,
                  overflowX: 'auto',
                  whiteSpace: 'pre',
                }}
              >
                {defect.snippet}
              </pre>
              <p style={{ margin: 0, fontSize: 12.5, fontStyle: 'italic', color: 'var(--text-3)', lineHeight: 1.5 }}>
                {defect.catch}
              </p>
            </div>
          ))}
        </div>
      </Section>

      <Section eyebrow="Say it out loud" title="What to tell the interviewer">
        <Pact>
          <ol style={{ margin: 0, paddingLeft: 20, display: 'grid', gap: 8 }}>
            {reviewHabits.defenseScripts.map((line) => (
              <li key={line} style={{ lineHeight: 1.6 }}>{line}</li>
            ))}
          </ol>
        </Pact>
      </Section>
    </StudyShell>
  );
}
