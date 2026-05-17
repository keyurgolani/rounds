import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Callout, Prose, Guidance, GuidanceGrid, Pact } from '../../shared/primitives';
import InfographicFrame from '../../shared/visuals/InfographicFrame';
import { aiCodingContent } from '../../content/aiCoding';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function MentalModel({ config, navGroups, scrollRef }: Props) {
  const { mentalModel } = aiCodingContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Mental Model`}
      title="AI Coding Mental Model"
      description="Trust the AI like a fast junior. Verify like a senior."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        title="Trust the junior. Verify like a senior."
        lede="The most useful frame for an AI coding round: treat the AI as a fast but fallible junior engineer. It can write plausible code quickly, but it doesn't read the spec as carefully as you do and it cannot run the hidden tests. Your job is to supply the judgment it lacks."
      >
        <Callout>{mentalModel.thesis}</Callout>
      </Section>

      <Section
        title="Three stages from AI output to ship"
        lede="Every integration follows the same loop: read what the AI produced, verify it against the original intent, then commit only what you can explain. Skipping the middle stage is where candidates lose points — the AI looks more correct than it is at a glance."
      >
        <InfographicFrame caption="Loop">
          <div
            className="grid"
            style={{
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 'var(--gap-sm)',
              width: '100%',
            }}
          >
            {mentalModel.trustVerifyStages.map((stage, idx) => {
              const isMiddle = idx === 1;
              return (
                <div
                  key={stage.stage}
                  style={{
                    minHeight: 140,
                    borderRadius: 'var(--radius)',
                    background: isMiddle ? 'var(--accent)' : 'var(--accent-soft)',
                    color: isMiddle ? 'var(--bg-elev)' : 'var(--accent)',
                    padding: 'var(--pad-md)',
                    display: 'grid',
                    gap: 'var(--gap-sm)',
                    alignContent: 'start',
                  }}
                >
                  <div
                    className="mono"
                    style={{
                      fontSize: 10.5,
                      fontWeight: 600,
                      letterSpacing: '0.1em',
                      textTransform: 'uppercase',
                      opacity: isMiddle ? 0.9 : 0.8,
                    }}
                  >
                    {idx + 1}. {stage.stage}
                  </div>
                  <div style={{ fontSize: 12.5, lineHeight: 1.5, opacity: isMiddle ? 0.95 : 0.9 }}>
                    {stage.do}
                  </div>
                </div>
              );
            })}
          </div>
        </InfographicFrame>
      </Section>

      <Section
        title="What 'verify' actually means"
        lede="Verification is not running the code and hoping the tests pass. It is tracing a concrete input through the logic yourself, checking every import is real, and confirming the edge cases the prompt named are actually handled — before you accept anything."
      >
        <GuidanceGrid>
          {mentalModel.verifyChecklist.map((item) => (
            <Guidance key={item} label={item}>
              Do this check before integrating the AI output, not after. A five-second trace now prevents a five-minute debugging session later.
            </Guidance>
          ))}
        </GuidanceGrid>
      </Section>

      <Section
        title="What to say out loud"
        lede="Interviewers award senior-level credit when they hear you narrate your review process. Silence while you read code reads as passive acceptance. Make your verification visible by speaking each check as you do it."
      >
        <Pact>{mentalModel.seniorSignal}</Pact>
        <Prose size="sm">
          Say this after each integration: what the AI got right, what it missed or misunderstood, and what you changed and why. This one habit separates a strong hire signal from a mid-level one.
        </Prose>
      </Section>
    </StudyShell>
  );
}
