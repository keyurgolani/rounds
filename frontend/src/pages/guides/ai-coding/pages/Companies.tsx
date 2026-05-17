import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig, AIPolicy } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Callout, Prose } from '../../shared/primitives';
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
      <Section
        title="AI-assisted rounds in industry"
        lede="Most large product companies are piloting or actively running AI-assisted coding formats as of 2026. Formats vary widely — live pairing, take-home, structured spec rounds, and real-codebase drop-ins are all in use. The AI policy (whether AI is required, optional, or prohibited) differs by company and sometimes by role level. The information below reflects reported formats; treat each row as a starting point, not a guarantee."
      >
        <Callout>
          Research the specific company's current format before each round — policies shift faster than guides get updated.
        </Callout>
      </Section>

      <Section
        title="Company-by-company expectations"
        lede="Each company below has a distinct emphasis: Meta grades engineering judgment, Shopify grades shipping speed, Stripe grades correctness and idempotency, and so on. Knowing the emphasis lets you weight your review time correctly and choose what to say out loud."
      >
        <div
          className="grid"
          style={{ gap: 'var(--gap-md)' }}
        >
          {companies.map((row) => (
            <article
              key={row.company}
              className="card"
              style={{
                padding: 'var(--pad-md)',
                display: 'grid',
                gap: 'var(--gap-sm)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap-sm)', flexWrap: 'wrap' }}>
                <strong style={{ fontSize: 16, color: 'var(--text)' }}>{row.company}</strong>
                <PolicyPill policy={row.aiPolicyDefault} />
              </div>

              <div
                className="grid"
                style={{
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: 'var(--gap-sm)',
                  paddingTop: 4,
                }}
              >
                <div>
                  <div
                    className="mono uppercase"
                    style={{ fontSize: 10.5, letterSpacing: '0.1em', color: 'var(--text-4)', marginBottom: 4 }}
                  >
                    Format
                  </div>
                  <Prose size="sm">{row.format}</Prose>
                </div>

                <div>
                  <div
                    className="mono uppercase"
                    style={{ fontSize: 10.5, letterSpacing: '0.1em', color: 'var(--text-4)', marginBottom: 4 }}
                  >
                    Time budget
                  </div>
                  <Prose size="sm">{row.timeBudgetMin} min</Prose>
                </div>

                <div>
                  <div
                    className="mono uppercase"
                    style={{ fontSize: 10.5, letterSpacing: '0.1em', color: 'var(--text-4)', marginBottom: 4 }}
                  >
                    Lean into
                  </div>
                  <Prose size="sm">{row.leanInto}</Prose>
                </div>
              </div>
            </article>
          ))}
        </div>
      </Section>

      <Section
        title="Do your own research before each round"
        lede="The details above are a starting point, not a source of truth. Companies change their formats on short cycles — a round described in a 2024 Blind thread may look completely different in 2026. The highest-signal research you can do is: read the company's recent engineering blog posts, search Blind and Glassdoor for reports from the last six months, and ask your recruiter directly about the AI policy and tooling provided in the room."
      >
        <Callout tone="muted">
          Ask your recruiter: "What AI tools, if any, will be available during the coding round, and is there a stated policy on using them?"
        </Callout>
        <Prose>
          A recruiter screen call is the best place to get this right. Most recruiters will answer directly, and knowing the policy in advance lets you practice in the correct mode rather than adapting on the fly.
        </Prose>
      </Section>
    </StudyShell>
  );
}
