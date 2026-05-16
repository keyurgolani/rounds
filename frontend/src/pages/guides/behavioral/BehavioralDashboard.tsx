import type { RefObject } from 'react';
import type { GuideNavGroup } from '../shared/GuideNav';
import type { TrackConfig } from '../guideTypes';
import StudyShell from '../shared/StudyShell';
import { Section, Pact, ChipRow } from '../shared/primitives';
import { behavioralContent } from '../content/behavioral';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function BehavioralDashboard({ config, navGroups, scrollRef }: Props) {
  const { dashboard } = behavioralContent;
  return (
    <StudyShell
      eyebrow={config.eyebrow}
      title={dashboard.title}
      description={dashboard.description}
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="STAR(R)" title="The time budget of a good answer">
        <StarTimeBudget segments={dashboard.starStrip} />
      </Section>

      <Section eyebrow="Signals" title="The trait portfolio behavioral rounds test">
        <ChipRow chips={dashboard.signalGrid.map((s) => s.name)} />
      </Section>

      <Section eyebrow="Pact" title="Evidence beats adjectives">
        <Pact>{dashboard.evidencePact}</Pact>
      </Section>

      <Section eyebrow="Amazon 2-5" title="Prep two stories per principle">
        <Pact>
          <p style={{ margin: 0 }}>{dashboard.amazonRule.intro}</p>
          <ul style={{ margin: '10px 0 0', paddingLeft: 18 }}>
            {dashboard.amazonRule.principles.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </Pact>
      </Section>
    </StudyShell>
  );
}

function StarTimeBudget({ segments }: { segments: { id: string; label: string; seconds: string; what: string }[] }) {
  // Width proportional to seconds; visual budget at a glance.
  const widths: Record<string, number> = { '15s': 11, '10s': 8, '60–90s': 52, '15–25s': 16, '10–20s': 13 };
  return (
    <div className="card" style={{ padding: 'var(--pad-md)', display: 'grid', gap: 'var(--gap-sm)' }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: segments.map((s) => `${widths[s.seconds] ?? 10}fr`).join(' '),
          gap: 4,
          overflow: 'hidden',
          borderRadius: 'var(--radius)',
        }}
      >
        {segments.map((segment, index) => (
          <div
            key={segment.id}
            style={{
              padding: '10px 12px',
              background: index === 2 ? 'var(--accent)' : 'var(--accent-soft)',
              color: index === 2 ? 'var(--bg-elev)' : 'var(--accent)',
              fontSize: 12.5,
              fontWeight: 600,
              textAlign: 'center',
            }}
          >
            {segment.label} · {segment.seconds}
          </div>
        ))}
      </div>
      <div className="grid" style={{ gap: 6 }}>
        {segments.map((segment) => (
          <div key={segment.id} className="grid" style={{ gridTemplateColumns: '110px 1fr', gap: 'var(--gap-sm)', alignItems: 'baseline' }}>
            <span className="mono" style={{ fontSize: 11, color: 'var(--text-4)', letterSpacing: '0.12em' }}>
              {segment.label.toUpperCase()}
            </span>
            <span style={{ color: 'var(--text-3)', fontSize: 13, lineHeight: 1.5 }}>{segment.what}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
