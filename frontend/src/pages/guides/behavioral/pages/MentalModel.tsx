import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, ThesisLine, LaneCard, Pact } from '../../shared/primitives';
import { behavioralContent } from '../../content/behavioral';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function MentalModel({ config, navGroups, scrollRef }: Props) {
  const { mentalModel } = behavioralContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Mental Model`}
      title="Behavioral Mental Model"
      description="Decode the signal first. Then bring evidence — not adjectives."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Thesis" title="Evidence beats adjectives">
        <ThesisLine>{mentalModel.thesis}</ThesisLine>
      </Section>

      <Section eyebrow="Decoder" title="Question opener → signal → evidence to bring">
        <div className="card" style={{ padding: 'var(--pad-md)', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>Opener</th>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>Signal</th>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>Evidence to bring</th>
              </tr>
            </thead>
            <tbody>
              {mentalModel.signalDecoder.map((row) => (
                <tr key={row.opener} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: 8, color: 'var(--text-2)', fontStyle: 'italic' }}>{row.opener}</td>
                  <td style={{ padding: 8, color: 'var(--accent)', fontWeight: 600 }}>{row.signal}</td>
                  <td style={{ padding: 8, color: 'var(--text-3)' }}>{row.evidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section eyebrow="STAR(R)" title="The anatomy of a good answer">
        <div
          className="grid"
          style={{ gap: 'var(--gap-sm)', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}
        >
          {mentalModel.starAnatomy.map((segment) => (
            <LaneCard
              key={segment.id}
              eyebrow={`${segment.label} · ${segment.seconds}`}
              title={segment.what}
            />
          ))}
        </div>
      </Section>

      <Section eyebrow="Defense" title="When the story has risk, defend the interpretation">
        <Pact>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {mentalModel.defendRiskyInterpretation.map((line) => (
              <li key={line} style={{ marginBottom: 6 }}>{line}</li>
            ))}
          </ul>
        </Pact>
      </Section>
    </StudyShell>
  );
}
