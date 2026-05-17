import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Prose, Guidance, GuidanceGrid, SubHeading } from '../../shared/primitives';
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
      <Section
        title="Four boxes that make a good prompt"
        lede="A prompt that reliably produces correct code has four parts. Leave any one out and the AI fills the gap with its best guess — which is almost always wrong on the hidden tests. Each box below closes a different failure mode."
      >
        <GuidanceGrid>
          {promptPlaybook.anatomy.map((box) => (
            <Guidance key={box.id} label={box.label}>
              {box.what}
            </Guidance>
          ))}
        </GuidanceGrid>
      </Section>

      <Section
        title="Reusable prompts to paste"
        lede="Each template below is structured around the four-box anatomy. Copy, fill in the placeholders in angle brackets, and read it once more before sending — a prompt you cannot read fluently in ten seconds is not tight enough."
      >
        <div className="grid" style={{ gap: 'var(--gap-md)' }}>
          {promptPlaybook.templates.map((template) => (
            <article
              key={template.id}
              className="card"
              style={{ padding: 'var(--pad-md)', display: 'grid', gap: 'var(--gap-sm)' }}
            >
              <strong style={{ fontSize: 15 }}>{template.label}</strong>
              <Prose>{template.purpose}</Prose>
              <pre
                style={{
                  margin: 0,
                  padding: 'var(--pad-md)',
                  background: 'var(--bg-sunken)',
                  borderRadius: 'var(--radius)',
                  boxShadow: 'inset 0 0 0 1px var(--border)',
                  fontSize: 12.5,
                  lineHeight: 1.55,
                  overflowX: 'auto',
                  whiteSpace: 'pre',
                  color: 'var(--text-2)',
                }}
              >
                <code>{template.template}</code>
              </pre>
              <Prose size="sm">{template.whyEachPart}</Prose>
            </article>
          ))}
        </div>
      </Section>

      <Section
        title="Don't write prompts like this"
        lede="These anti-patterns are the most common causes of a plausible-looking result that fails hidden tests. Each one leaves a gap that the AI fills with its own interpretation — and that interpretation is rarely the one the spec required."
      >
        <div className="grid" style={{ gap: 'var(--gap-md)' }}>
          {promptPlaybook.antiTemplates.map((anti) => (
            <div
              key={anti.bad}
              className="card"
              style={{ padding: 'var(--pad-md)', display: 'grid', gap: 'var(--gap-sm)' }}
            >
              <SubHeading>
                <span className="mono" style={{ fontSize: 13 }}>{anti.bad}</span>
              </SubHeading>
              <Prose size="sm">{anti.why}</Prose>
            </div>
          ))}
        </div>
      </Section>
    </StudyShell>
  );
}
