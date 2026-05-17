import type { RefObject } from 'react';
import type { GuideNavGroup } from '../shared/GuideNav';
import type { TrackConfig } from '../guideTypes';
import StudyShell from '../shared/StudyShell';
import { Section, Callout, Prose, Guidance, GuidanceGrid, LaneCard } from '../shared/primitives';
import { aiCodingContent } from '../content/aiCoding';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function AICodingDashboard({ config, navGroups, scrollRef }: Props) {
  const { dashboard } = aiCodingContent;
  return (
    <StudyShell
      eyebrow={config.eyebrow}
      title={dashboard.title}
      description={dashboard.description}
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        title="What AI coding rounds actually test"
        lede="An AI-assisted round tests two skills at once: can you steer the AI to good code, and can you tell when it's wrong? Both matter. The interviewer is watching the cycle of prompt → output → review → fix — not the number of lines the AI wrote."
      >
        <Callout>{dashboard.whatThisTests}</Callout>
      </Section>

      <Section
        title="Round formats you will encounter"
        lede="Companies run AI coding rounds in several distinct flavors. Each flavor stresses a different skill — knowing which one you're in shapes how you should open, where you spend your time, and what the interviewer is grading you on."
      >
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--gap-md)' }}
        >
          {dashboard.flavorMatrix.map((card) => (
            <LaneCard
              key={card.id}
              eyebrow={card.label}
              title={card.tests}
              body={<span><strong style={{ color: 'var(--text-2)' }}>Move:</strong> {card.dominantMove}</span>}
              footer={<span><strong style={{ color: 'var(--text-3)' }}>Trap:</strong> {card.trap}</span>}
            />
          ))}
        </div>
      </Section>

      <Section
        title="Where you see AI-assisted rounds"
        lede="Most large product companies are piloting or actively running AI-assisted formats as of 2026. Formats and policies vary by team and role level — always verify the current format directly with your recruiter or from recent candidate writeups."
      >
        <GuidanceGrid>
          {dashboard.companies.map((company) => (
            <Guidance key={company} label={company}>
              Check engineering blogs, Blind, and recent Glassdoor reports for the current AI policy and format details at this company before your round.
            </Guidance>
          ))}
        </GuidanceGrid>
      </Section>

      <Section
        title="Typical time budget"
        lede="Most AI-assisted rounds run 45–60 minutes. The clock pressure is intentional: you are expected to use the AI to move faster, not to produce more code. Pace your loops so you always have time to review before the session ends."
      >
        <Prose>{dashboard.timeBudget} is the typical window. Aim to close each prompt–review–integrate loop in under five minutes.</Prose>
      </Section>
    </StudyShell>
  );
}
