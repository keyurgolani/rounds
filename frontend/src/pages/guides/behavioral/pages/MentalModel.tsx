import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Callout, GuidanceGrid, Guidance, Pact } from '../../shared/primitives';
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
      <Section title="Evidence beats adjectives">
        <Callout>{mentalModel.thesis}</Callout>
      </Section>

      <Section
        eyebrow="Decoder"
        title="Question opener → signal → evidence to bring"
        lede="Behavioral rounds are signal-finding exercises. Each opener maps to a specific competency the interviewer needs to confirm — and your job is to recognize the signal first, then pick the anecdote that demonstrates it. The table below gives you the translation layer: opener → signal → what concrete evidence makes the story land."
      >
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

      <Section
        eyebrow="Defense"
        title="When the story has risk, defend the interpretation"
        lede="Some of the most credible stories involve failure, disagreement, or escalation — situations that could read as red flags if left unframed. The moves below let you surface a difficult story without letting the interviewer fill in the worst interpretation. Use them proactively, not defensively."
      >
        <GuidanceGrid>
          {mentalModel.defendRiskyInterpretation.map((line) => {
            const [label, ...rest] = line.split(':');
            return (
              <Guidance key={line} label={label.trim()}>
                {rest.length > 0 ? rest.join(':').trim() : line}
              </Guidance>
            );
          })}
        </GuidanceGrid>
        <Pact>
          The STAR framework (Situation / Task / Action / Result / Reflection) is covered in the{' '}
          <strong>Field Guide</strong> with the full time-budget breakdown. Return there for the
          anatomy of a good answer; this page focuses on signal recognition and defensive framing.
        </Pact>
      </Section>
    </StudyShell>
  );
}
