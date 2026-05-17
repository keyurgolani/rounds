import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig, AIPolicy, AICompanyRow } from '../../guideTypes';
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

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="mono uppercase"
      style={{ fontSize: 10.5, letterSpacing: '0.1em', color: 'var(--text-4)', marginBottom: 4 }}
    >
      {children}
    </div>
  );
}

function CompanyCard({ row }: { row: AICompanyRow }) {
  return (
    <article
      className="card"
      style={{
        padding: 'var(--pad-md)',
        display: 'grid',
        gap: 'var(--gap-sm)',
        height: '100%',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap-sm)', flexWrap: 'wrap' }}>
        <strong style={{ fontSize: 16, color: 'var(--text)' }}>{row.company}</strong>
        <PolicyPill policy={row.aiPolicyDefault} />
        <span className="mono" style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--text-4)' }}>
          {row.timeBudgetMin} min
        </span>
      </div>

      <div>
        <FieldLabel>Format</FieldLabel>
        <Prose size="sm">{row.format}</Prose>
      </div>

      {row.tools && (
        <div>
          <FieldLabel>Tools</FieldLabel>
          <Prose size="sm">{row.tools}</Prose>
        </div>
      )}

      {row.rubric && (
        <div>
          <FieldLabel>Rubric</FieldLabel>
          <Prose size="sm">{row.rubric}</Prose>
        </div>
      )}

      <div>
        <FieldLabel>Lean into</FieldLabel>
        <Prose size="sm">{row.leanInto}</Prose>
      </div>

      {row.followUps && (
        <div>
          <FieldLabel>Common follow-ups</FieldLabel>
          <Prose size="sm">{row.followUps}</Prose>
        </div>
      )}

      {row.sources && row.sources.length > 0 && (
        <details
          style={{
            marginTop: 4,
            paddingTop: 8,
            borderTop: '1px dashed var(--border)',
          }}
        >
          <summary
            className="mono uppercase"
            style={{
              fontSize: 10,
              letterSpacing: '0.1em',
              color: 'var(--text-4)',
              cursor: 'pointer',
              listStyle: 'none',
            }}
          >
            Sources ({row.sources.length})
          </summary>
          <ul
            style={{
              margin: '6px 0 0',
              paddingLeft: 16,
              fontSize: 11.5,
              lineHeight: 1.5,
              color: 'var(--text-3)',
            }}
          >
            {row.sources.map((src, i) => (
              <li key={i} style={{ marginBottom: 2 }}>{src}</li>
            ))}
          </ul>
        </details>
      )}
    </article>
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
        lede="Each card surfaces the round structure, AI tooling that's allowed or provided, the rubric the interviewer is grading against, and the most actionable thing to lean into. Sources are linked at the bottom of each card so you can audit the claim and check freshness before each round."
      >
        <div
          className="grid"
          style={{
            gap: 'var(--gap-md)',
            gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))',
            alignItems: 'stretch',
          }}
        >
          {companies.map((row) => (
            <CompanyCard key={row.company} row={row} />
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
