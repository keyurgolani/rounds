import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Prose, Pact } from '../../shared/primitives';
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
      description="Weak → strong rewrites and a self-scorecard rubric to diagnose and fix vague responses."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        eyebrow="Rewrites"
        title="Weak phrase → what's missing → strong rewrite"
        lede="Each pair below starts with a phrase that sounds reasonable but scores poorly, explains the underlying gap, and shows the rewrite. The pattern is consistent: weak answers lack an actor, a decision criterion, or a quantified result. Study the rewrites until the repair move becomes automatic."
      >
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

      <Section
        eyebrow="Scorecard"
        title="Score yourself 1–3 across five dimensions"
        lede="Use this rubric after recording a practice answer. Score each dimension honestly — a 2 on Ownership or a 1 on Impact means the answer is likely to score below bar regardless of how good the underlying story is. The goal is a minimum 2 on every dimension, with 3s on Specificity and Impact."
      >
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
        <Prose size="sm">
          If you scored a 1 on Ownership, revisit the Repair rewrites above — every rewrite with "no actor" in the missing column shows the fix. If you scored a 1 on Reflection, see the{' '}
          <strong>Cheatsheet</strong> for examples of behavior-proof lessons versus generic ones.
        </Prose>
      </Section>

      <Section
        eyebrow="Drill"
        title="30-minute mock practice loop"
        lede="Prep without a drill loop doesn't transfer to performance under pressure. Run this cycle for each story in your library — once is enough to expose the weak spots, twice is enough to fix them. The goal is to be able to tell any story cold, to time, without notes."
      >
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
