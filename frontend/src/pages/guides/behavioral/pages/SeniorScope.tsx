import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Pact } from '../../shared/primitives';
import { behavioralContent } from '../../content/behavioral';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function SeniorScope({ config, navGroups, scrollRef }: Props) {
  const { seniorScope } = behavioralContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Senior Scope`}
      title="Senior Scope"
      description="Show scope in numbers. Show judgment in criteria. Defend the risky interpretation."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Ladder" title="Mid → Principal — what scope looks like at each tier">
        <ol style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 'var(--gap-md)' }}>
          {seniorScope.ladder.map((tier, index) => (
            <li
              key={tier.level}
              className="card"
              style={{
                padding: 'var(--pad-md)',
                display: 'grid',
                gap: 'var(--gap-sm)',
                gridTemplateColumns: 'auto minmax(0, 1fr)',
                alignItems: 'start',
              }}
            >
              <span
                className="mono"
                style={{
                  width: 36, height: 36,
                  display: 'grid', placeItems: 'center',
                  borderRadius: 999,
                  background: 'var(--accent-soft)',
                  color: 'var(--accent)',
                  fontSize: 11,
                  fontWeight: 600,
                }}
              >
                T{index + 1}
              </span>
              <div className="grid" style={{ gap: 6 }}>
                <strong style={{ fontSize: 15, fontWeight: 600 }}>{tier.label}</strong>
                <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.5 }}>
                  {tier.examples.map((example) => <li key={example}>{example}</li>)}
                </ul>
                <div className="flex flex-wrap" style={{ gap: 6 }}>
                  {tier.numbers.map((number) => (
                    <span
                      key={number}
                      className="pill mono"
                      style={{
                        background: 'var(--bg-sunken)',
                        color: 'var(--text-2)',
                        boxShadow: 'inset 0 0 0 1px var(--border)',
                        fontSize: 11,
                      }}
                    >
                      {number}
                    </span>
                  ))}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <Section eyebrow="Frame" title="Six elements every senior answer has">
        <Pact>
          <ol style={{ margin: 0, paddingLeft: 18 }}>
            {seniorScope.answerFrame.map((line) => (
              <li key={line} style={{ marginBottom: 6 }}>{line}</li>
            ))}
          </ol>
        </Pact>
      </Section>

      <Section eyebrow="Defense" title="Defensive framing for risky stories">
        <div className="grid" style={{ gap: 'var(--gap-sm)', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}>
          {seniorScope.defensiveFraming.map((entry) => (
            <div key={entry.case} className="card" style={{ padding: 'var(--pad-sm)' }}>
              <strong style={{ display: 'block', fontSize: 13, fontWeight: 600 }}>{entry.case}</strong>
              <p style={{ margin: '6px 0 0', color: 'var(--text-3)', fontSize: 12.5, lineHeight: 1.5 }}>{entry.reframe}</p>
            </div>
          ))}
        </div>
      </Section>
    </StudyShell>
  );
}
