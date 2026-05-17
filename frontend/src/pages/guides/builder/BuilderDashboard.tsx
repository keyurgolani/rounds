import type { RefObject } from 'react';
import type { GuideNavGroup } from '../shared/GuideNav';
import type { TrackConfig } from '../guideTypes';
import StudyShell from '../shared/StudyShell';
import {
  Section,
  Callout,
  Prose,
  Pact,
  GuidanceGrid,
  Guidance,
  LaneCard,
} from '../shared/primitives';
import { builderContent } from '../content/builder';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function BuilderDashboard({ config, navGroups, scrollRef }: Props) {
  const { dashboard } = builderContent;

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
        id="take-home-reframe"
        title="This is a take-home, not a timed exam"
        lede="When a company gives you a Real-World Problem prompt, you have days — sometimes weeks — to submit. You have the entire internet, AI tooling, and any framework you choose at your disposal. The bar isn't 'did you solve it in 45 minutes' — it's 'did you ship something that demonstrates judgment, taste, and engineering craft?'"
      >
        <Prose>
          Real-World Problems are evaluated on what you submit, not how fast you typed it. Reviewers
          spend more time reading your README and walking your commit history than running your code.
          Judgment, taste, and documentation quality matter more than the number of features you
          shipped.
        </Prose>
        <Callout>
          AI is expected. Reviewers know you used it. The grade is whether you understood, edited,
          and can defend every line — not whether you typed it.
        </Callout>
      </Section>

      <Section
        eyebrow="Flavors"
        title="Four flavors of real-world problems"
        lede="Every prompt falls into one of these four shapes. Recognizing the shape early lets you pick the right opening move — and avoid the trap that sinks most submissions in that domain."
      >
        <div
          className="grid"
          style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
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
        eyebrow="AI Policy"
        title="AI policy varies by prompt"
        lede="Most Real-World Problem prompts explicitly permit AI tooling — and a growing number require it. A minority ask you to work without it. Read the prompt carefully before you open a chat window."
      >
        <GuidanceGrid>
          <Guidance label="AI off">
            The prompt explicitly prohibits code generation. Write every line yourself. Note this
            clearly in the README. When in doubt, ask the company what counts as prohibited — a
            web search is a gray area, a code-generation call is not.
          </Guidance>
          <Guidance label="Candidate choice">
            Use AI deliberately. Own the output. In the README, briefly note which parts were
            AI-assisted and how you reviewed them. Reviewers want to see intent and judgment, not
            abstinence.
          </Guidance>
          <Guidance label="AI on (most common)">
            Use AI freely, but verify every output before it ships. Your README should include a
            short AI-usage note explaining what was generated, what you changed, and what you
            verified manually. This is the primary signal reviewers evaluate.
          </Guidance>
        </GuidanceGrid>
      </Section>

      <Section eyebrow="Time" title="Budget your days, not your minutes">
        <GuidanceGrid>
          {dashboard.timeTiers.map((tier) => (
            <Guidance key={tier} label={tier}>
              See the Time Plan page for a phase breakdown scaled to this budget.
            </Guidance>
          ))}
        </GuidanceGrid>
      </Section>

      <Section eyebrow="Pact" title="What 'submitted' means">
        <Pact>{dashboard.submissionPact}</Pact>
      </Section>
    </StudyShell>
  );
}
