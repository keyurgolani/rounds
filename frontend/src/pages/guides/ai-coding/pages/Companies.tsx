import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig, AIPolicy } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section } from '../../shared/primitives';
import { aiCodingContent } from '../../content/aiCoding';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

function PolicyPill({ policy }: { policy: AIPolicy }) {
  const palette = {
    off: { bg: 'var(--bg-sunken)', fg: 'var(--text-3)' },
    'candidate-choice': { bg: 'var(--accent-soft)', fg: 'var(--accent)' },
    on: { bg: 'var(--accent)', fg: 'var(--bg-elev)' },
  } as const;
  const p = palette[policy];
  return (
    <span
      className="pill mono"
      style={{ background: p.bg, color: p.fg, boxShadow: 'none', fontSize: 10.5 }}
    >
      {policy.toUpperCase()}
    </span>
  );
}

export default function Companies({ config, navGroups, scrollRef }: Props) {
  const companies = aiCodingContent.companies;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Companies`}
      title="Companies"
      description="What to expect by company — format, time budget, AI policy default, what to lean into."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Companies" title="Company-by-company expectations">
        <div className="card" style={{ padding: 'var(--pad-md)', overflowX: 'auto' }}>
          <table
            style={{
              borderCollapse: 'separate',
              borderSpacing: 4,
              minWidth: 560,
              width: '100%',
              fontSize: 13,
            }}
          >
            <thead>
              <tr>
                {['Company', 'Format', 'Time (min)', 'AI Policy', 'Lean into'].map((col) => (
                  <th
                    key={col}
                    style={{
                      textAlign: 'left',
                      padding: '6px 8px',
                      color: 'var(--text-4)',
                      fontWeight: 500,
                      fontSize: 11,
                      letterSpacing: '0.05em',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {companies.map((row) => (
                <tr key={row.company}>
                  <td style={{ padding: '8px', fontWeight: 700, color: 'var(--text)', whiteSpace: 'nowrap' }}>
                    {row.company}
                  </td>
                  <td style={{ padding: '8px', color: 'var(--text-2)', lineHeight: 1.45, fontSize: 12.5 }}>
                    {row.format}
                  </td>
                  <td className="mono" style={{ padding: '8px', color: 'var(--text-2)', whiteSpace: 'nowrap', fontSize: 12 }}>
                    {row.timeBudgetMin}
                  </td>
                  <td style={{ padding: '8px' }}>
                    <PolicyPill policy={row.aiPolicyDefault} />
                  </td>
                  <td style={{ padding: '8px', color: 'var(--text-2)', lineHeight: 1.45, fontSize: 12.5 }}>
                    {row.leanInto}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </StudyShell>
  );
}
