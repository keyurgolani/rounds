import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, LaneCard } from '../../shared/primitives';
import { codingContent } from '../../content/coding';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

const CELL_COLORS = {
  pass: { bg: 'var(--status-pass-soft)', fg: 'var(--status-pass)' },
  warn: { bg: 'var(--status-warn-soft)', fg: 'var(--status-warn)' },
  fail: { bg: 'var(--status-fail-soft)', fg: 'var(--status-fail)' },
} as const;

export default function Complexity({ config, navGroups, scrollRef }: Props) {
  const { complexity } = codingContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Complexity`}
      title="Complexity Compass"
      description="What inputs allow what complexity classes — and which patterns naturally hit each target."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Compass" title="Input size × complexity class">
        <div
          className="card"
          style={{
            padding: 'var(--pad-md)',
            overflowX: 'auto',
          }}
        >
          <table
            style={{
              borderCollapse: 'separate',
              borderSpacing: 4,
              minWidth: 560,
              width: '100%',
              fontSize: 12,
            }}
          >
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: 6, color: 'var(--text-4)', fontWeight: 500 }}>↓ input · class →</th>
                {complexity.compass.cols.map((col) => (
                  <th key={col} className="mono" style={{ padding: 6, color: 'var(--text-3)', fontWeight: 500, textAlign: 'center' }}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {complexity.compass.rows.map((row) => (
                <tr key={row}>
                  <td className="mono" style={{ padding: 6, color: 'var(--text-2)', fontSize: 11.5 }}>{row}</td>
                  {complexity.compass.cols.map((col) => {
                    const cell = complexity.compass.cells.find((c) => c.row === row && c.col === col);
                    const palette = cell ? CELL_COLORS[cell.status] : { bg: 'var(--bg-sunken)', fg: 'var(--text-4)' };
                    return (
                      <td
                        key={`${row}-${col}`}
                        style={{
                          padding: '6px 0',
                          borderRadius: 'var(--radius)',
                          background: palette.bg,
                          color: palette.fg,
                          textAlign: 'center',
                          fontWeight: 600,
                          textTransform: 'uppercase',
                          fontSize: 10.5,
                        }}
                      >
                        {cell?.status ?? '—'}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section eyebrow="Constraint → Target" title="What to aim for at each input band">
        <div
          className="grid"
          style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}
        >
          {complexity.constraintTargets.map((entry) => (
            <LaneCard
              key={entry.inputBand}
              eyebrow={entry.inputBand}
              title={entry.target}
              body={
                <div className="flex flex-wrap" style={{ gap: 6 }}>
                  {entry.naturalPatterns.map((pattern) => (
                    <span key={pattern} className="pill" style={{ background: 'var(--accent-soft)', color: 'var(--accent)', boxShadow: 'none', fontSize: 11 }}>
                      {pattern}
                    </span>
                  ))}
                </div>
              }
            />
          ))}
        </div>
      </Section>

      <Section eyebrow="Proof Language" title="What to say to prove correctness">
        <ul className="grid" style={{ gap: 6, margin: 0, padding: 0, listStyle: 'none' }}>
          {complexity.proofLanguage.map((line) => (
            <li key={line} style={{ paddingLeft: 14, position: 'relative', color: 'var(--text-2)', fontSize: 13.5 }}>
              <span style={{ position: 'absolute', left: 0, color: 'var(--accent)' }}>•</span>
              {line}
            </li>
          ))}
        </ul>
      </Section>

      <Section eyebrow="Cost Reference" title="Standard time costs to keep in your head">
        <div
          className="grid"
          style={{ gap: 'var(--gap-sm)', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
        >
          {complexity.costReference.map((entry) => (
            <div
              key={entry.op}
              className="card"
              style={{ padding: 'var(--pad-sm)' }}
            >
              <div style={{ fontSize: 13, color: 'var(--text-2)', fontWeight: 500 }}>{entry.op}</div>
              <div className="mono" style={{ marginTop: 4, fontSize: 12, color: 'var(--accent)' }}>{entry.cost}</div>
            </div>
          ))}
        </div>
      </Section>
    </StudyShell>
  );
}
