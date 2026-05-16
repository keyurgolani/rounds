import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section } from '../../shared/primitives';
import { behavioralContent } from '../../content/behavioral';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function StoryBank({ config, navGroups, scrollRef }: Props) {
  const { storyBank } = behavioralContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Story Bank`}
      title="Story Bank"
      description="Eight signals × four evidence dimensions. Build your portfolio before the loop, not during it."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Portfolio" title="What good evidence looks like for each signal">
        <div
          className="grid"
          style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}
        >
          {storyBank.signals.map((signal) => (
            <article
              key={signal.key}
              className="card"
              style={{ padding: 'var(--pad-md)', display: 'grid', gap: 'var(--gap-sm)' }}
            >
              <div className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.12em' }}>
                SIGNAL
              </div>
              <strong style={{ fontSize: 15, fontWeight: 600 }}>{signal.name}</strong>
              <DimensionList label="Artifacts"    items={signal.artifacts} />
              <DimensionList label="Metrics"      items={signal.metrics} />
              <DimensionList label="Stakeholders" items={signal.stakeholders} />
              <DimensionList label="Criteria"     items={signal.criteria} />
            </article>
          ))}
        </div>
      </Section>

      <Section eyebrow="Format" title="Canonical story entry">
        <div className="card" style={{ padding: 'var(--pad-md)' }}>
          <dl style={{ margin: 0, display: 'grid', gap: 'var(--gap-sm)' }}>
            {storyBank.storyFormat.map((row) => (
              <div key={row.field} className="grid" style={{ gridTemplateColumns: '110px 1fr', gap: 'var(--gap-sm)', alignItems: 'baseline' }}>
                <dt className="mono" style={{ fontSize: 11, color: 'var(--text-4)', letterSpacing: '0.12em' }}>
                  {row.field.toUpperCase()}
                </dt>
                <dd style={{ margin: 0, color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.55 }}>{row.example}</dd>
              </div>
            ))}
          </dl>
        </div>
      </Section>

      <Section eyebrow="Angles" title="One story → many prompts">
        <div className="grid" style={{ gap: 'var(--gap-sm)', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
          {storyBank.reusableAngles.map((entry) => (
            <div key={entry.angle} className="card" style={{ padding: 'var(--pad-sm)' }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-2)' }}>{entry.angle}</div>
              <div style={{ marginTop: 4, color: 'var(--text-3)', fontSize: 12.5, lineHeight: 1.45 }}>{entry.lead}</div>
            </div>
          ))}
        </div>
      </Section>
    </StudyShell>
  );
}

function DimensionList({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="grid" style={{ gap: 4 }}>
      <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)', letterSpacing: '0.12em' }}>{label.toUpperCase()}</span>
      <div className="flex flex-wrap" style={{ gap: 4 }}>
        {items.map((item) => (
          <span
            key={item}
            className="pill"
            style={{
              background: 'var(--bg-sunken)',
              color: 'var(--text-2)',
              boxShadow: 'inset 0 0 0 1px var(--border)',
              fontSize: 11,
            }}
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
