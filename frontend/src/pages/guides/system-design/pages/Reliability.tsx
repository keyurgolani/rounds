import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, LaneCard, Pact } from '../../shared/primitives';
import { systemDesignContent } from '../../content/systemDesign';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function Reliability({ config, navGroups, scrollRef }: Props) {
  const { reliability } = systemDesignContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Reliability`}
      title="Reliability"
      description="Failure modes are the half of the round that separates senior from staff. Pick the failure that hurts the user, then state mitigation + metric + recovery."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Failure Menu" title="Failure → mitigation">
        <div
          className="grid"
          style={{ gap: 'var(--gap-sm)', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}
        >
          {reliability.failureMenu.map((row) => (
            <article
              key={row.failure}
              className="card"
              style={{ padding: 'var(--pad-md)' }}
            >
              <div className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.12em' }}>FAILURE</div>
              <strong style={{ display: 'block', marginTop: 6, fontSize: 14, fontWeight: 600 }}>{row.failure}</strong>
              <div className="mono" style={{ marginTop: 12, fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.12em' }}>MITIGATION</div>
              <p style={{ margin: '6px 0 0', color: 'var(--text-3)', fontSize: 13, lineHeight: 1.5 }}>{row.mitigation}</p>
            </article>
          ))}
        </div>
      </Section>

      <Section eyebrow="Patterns" title="Pattern → what it handles → risk it creates">
        <div
          className="grid"
          style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}
        >
          {reliability.patterns.map((entry) => (
            <LaneCard
              key={entry.id}
              eyebrow="Pattern"
              title={entry.pattern}
              body={<span><strong style={{ color: 'var(--text-2)' }}>Handles:</strong> {entry.handles}</span>}
              footer={`Risk: ${entry.risk}`}
            />
          ))}
        </div>
      </Section>

      <Section eyebrow="Senior Framing" title="How staff talks about reliability">
        <Pact>
          <ol style={{ margin: 0, paddingLeft: 18 }}>
            {reliability.seniorFraming.map((line) => (
              <li key={line} style={{ marginBottom: 6 }}>{line}</li>
            ))}
          </ol>
        </Pact>
      </Section>
    </StudyShell>
  );
}
