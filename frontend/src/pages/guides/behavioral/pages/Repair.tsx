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

export default function Repair({ config, navGroups, scrollRef }: Props) {
  const { repair } = behavioralContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Repair`}
      title="Answer Repair"
      description="Weak → strong rewrites, a self-scorecard rubric, and a 30-minute mock drill loop."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Rewrites" title="Weak phrase → what's missing → strong rewrite">
        <div className="grid" style={{ gap: 'var(--gap-md)' }}>
          {repair.rewrites.map((pair, index) => (
            <article
              key={index}
              className="card"
              style={{
                padding: 'var(--pad-md)',
                display: 'grid',
                gap: 'var(--gap-sm)',
                gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)',
              }}
            >
              <div>
                <div className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.12em' }}>WEAK</div>
                <p style={{ margin: '6px 0 0', color: 'var(--text-3)', fontSize: 13, lineHeight: 1.5, fontStyle: 'italic' }}>{pair.weak}</p>
              </div>
              <div>
                <div className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.12em' }}>WHAT'S MISSING</div>
                <p style={{ margin: '6px 0 0', color: 'var(--text-3)', fontSize: 13, lineHeight: 1.5 }}>{pair.missing}</p>
              </div>
              <div
                style={{
                  paddingLeft: 12,
                  boxShadow: 'inset 3px 0 0 var(--accent)',
                }}
              >
                <div className="mono" style={{ fontSize: 10.5, color: 'var(--accent)', letterSpacing: '0.12em' }}>STRONG</div>
                <p style={{ margin: '6px 0 0', color: 'var(--text-2)', fontSize: 13, lineHeight: 1.5 }}>{pair.strong}</p>
              </div>
            </article>
          ))}
        </div>
      </Section>

      <Section eyebrow="Scorecard" title="Score yourself 1-3 across five dimensions">
        <div className="card" style={{ padding: 'var(--pad-md)', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>Dimension</th>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>1 — weak</th>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>2 — passable</th>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>3 — strong</th>
              </tr>
            </thead>
            <tbody>
              {repair.scorecardDimensions.map((row) => (
                <tr key={row.name} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: 8, color: 'var(--text-2)', fontWeight: 500 }}>{row.name}</td>
                  <td style={{ padding: 8, color: 'var(--text-3)' }}>{row.one}</td>
                  <td style={{ padding: 8, color: 'var(--text-3)' }}>{row.two}</td>
                  <td style={{ padding: 8, color: 'var(--accent)', fontWeight: 600 }}>{row.three}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section eyebrow="Drill" title="30-minute mock practice loop">
        <Pact>
          <ol style={{ margin: 0, paddingLeft: 18 }}>
            {repair.mockDrillSteps.map((step) => (
              <li key={step} style={{ marginBottom: 6 }}>{step}</li>
            ))}
          </ol>
        </Pact>
      </Section>
    </StudyShell>
  );
}
