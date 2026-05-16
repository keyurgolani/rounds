import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, ThesisLine, LaneCard, Pact } from '../../shared/primitives';
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
      <Section eyebrow="Thesis" title="Trust the junior. Verify like a senior.">
        <ThesisLine>{mentalModel.thesis}</ThesisLine>
      </Section>

      <Section eyebrow="Flow" title="Three stages from AI output to ship">
        <InfographicFrame caption="Loop" minHeight={180}>
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

      <Section eyebrow="Verify" title="What 'verify' actually means">
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 'var(--gap-sm)' }}
        >
          {mentalModel.verifyChecklist.map((item) => (
            <LaneCard key={item} title={item} />
          ))}
        </div>
      </Section>

      <Section eyebrow="Senior Signal" title="What to say out loud">
        <Pact>{mentalModel.seniorSignal}</Pact>
      </Section>
    </StudyShell>
  );
}
