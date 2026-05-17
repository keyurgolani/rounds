import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Prose, Guidance, GuidanceGrid, Pact } from '../../shared/primitives';
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
      <Section
        title="Review every AI output along five axes"
        lede="A review is not a vibe check. Each of these five dimensions catches a different class of AI mistake — working through all five in order takes about sixty seconds and prevents the majority of hidden-test failures."
      >
        <GuidanceGrid>
          {reviewHabits.checklist.map((item) => (
            <Guidance key={item.dim} label={item.dim}>
              {item.check}
            </Guidance>
          ))}
        </GuidanceGrid>
      </Section>

      <Section
        title="What AI gets wrong, with examples"
        lede="These are the defect classes that appear most frequently in AI-generated code during interviews. Each one is subtle enough to pass a quick read and the visible tests — which is exactly why it costs candidates points when it slips through."
      >
        <div
          className="grid"
          style={{ gap: 'var(--gap-md)' }}
        >
          {reviewHabits.defects.map((defect) => (
            <article
              key={defect.id}
              className="card"
              style={{
                padding: 'var(--pad-md)',
                display: 'grid',
                gap: 'var(--gap-sm)',
              }}
            >
              <strong style={{ fontSize: 15, color: 'var(--text)' }}>{defect.defect}</strong>
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
              <Prose size="sm">{defect.catch}</Prose>
            </article>
          ))}
        </div>
      </Section>

      <Section
        title="What to tell the interviewer"
        lede="Speaking your review out loud is itself a signal. These scripts show you how to articulate the defect you caught, what the correct behavior should be, and why the AI's version fell short — without sounding like you're criticizing the tool."
      >
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
