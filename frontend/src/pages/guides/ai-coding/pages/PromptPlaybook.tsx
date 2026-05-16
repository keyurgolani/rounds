import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, LaneCard } from '../../shared/primitives';
import { aiCodingContent } from '../../content/aiCoding';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function PromptPlaybook({ config, navGroups, scrollRef }: Props) {
  const { promptPlaybook } = aiCodingContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Prompt Playbook`}
      title="Prompt Playbook"
      description="Anatomy, paste-ready templates, anti-patterns."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Anatomy" title="Four boxes that make a good prompt">
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--gap-sm)' }}
        >
          {promptPlaybook.anatomy.map((box) => (
            <LaneCard key={box.id} eyebrow={box.label} title={box.what} />
          ))}
        </div>
      </Section>

      <Section eyebrow="Templates" title="Reusable prompts to paste">
        <div className="grid" style={{ gap: 'var(--gap-sm)' }}>
          {promptPlaybook.templates.map((template) => (
            <details
              key={template.id}
              style={{
                borderRadius: 'var(--radius)',
                background: 'var(--bg-elev)',
                boxShadow: 'inset 0 0 0 1px var(--border)',
                overflow: 'hidden',
              }}
            >
              <summary
                style={{
                  padding: 'var(--pad-md)',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 4,
                  listStyle: 'none',
                }}
              >
                <strong style={{ fontSize: 14, lineHeight: 1.3, fontWeight: 600, color: 'var(--text)' }}>
                  {template.label}
                </strong>
                <span style={{ fontSize: 12.5, color: 'var(--text-3)', lineHeight: 1.45 }}>
                  {template.purpose}
                </span>
              </summary>
              <div style={{ padding: 'var(--pad-md)', paddingTop: 0, display: 'grid', gap: 'var(--gap-sm)' }}>
                <pre
                  className="mono"
                  style={{
                    margin: 0,
                    padding: 'var(--pad-md)',
                    background: 'var(--bg-sunken)',
                    borderRadius: 'var(--radius)',
                    boxShadow: 'inset 0 0 0 1px var(--border)',
                    color: 'var(--text-2)',
                    fontSize: 12,
                    lineHeight: 1.55,
                    overflowX: 'auto',
                    whiteSpace: 'pre',
                  }}
                >
                  {template.template}
                </pre>
                <p style={{ margin: 0, fontSize: 12, fontStyle: 'italic', color: 'var(--text-3)', lineHeight: 1.5 }}>
                  {template.whyEachPart}
                </p>
              </div>
            </details>
          ))}
        </div>
      </Section>

      <Section eyebrow="Avoid" title="Don't write prompts like this">
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--gap-sm)' }}
        >
          {promptPlaybook.antiTemplates.map((anti) => (
            <LaneCard
              key={anti.bad}
              title={<span className="mono" style={{ fontSize: 13 }}>{anti.bad}</span>}
              body={anti.why}
            />
          ))}
        </div>
      </Section>
    </StudyShell>
  );
}
