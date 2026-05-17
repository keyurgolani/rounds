import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Callout, Prose, Pact, SubHeading } from '../../shared/primitives';
import TimelineStrip from '../../shared/visuals/TimelineStrip';
import { builderContent } from '../../content/builder';
import { useInterviewLength } from '../../shared/useInterviewLength';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function TimePlan({ config, navGroups, scrollRef }: Props) {
  const { timePlan } = builderContent;
  const [preset] = useInterviewLength('builder');

  // Find the plan matching the active preset, or fall back to the first.
  const activePlan =
    timePlan.plans.find((p) => p.presetId === preset.id) ?? timePlan.plans[0];

  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Time Plan`}
      title="Time Plans"
      description="Day-by-day phase budgets for 1-day, 3-day, 1-week, and 2-week take-homes."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        title="Think in days, not minutes"
        lede="A take-home is a writing exercise stretched across real calendar time. The first day is for understanding the problem and proving the core works. The middle bulk is for building. The last stretch is entirely for documentation and polish — because reviewers read the README before they run the code."
      >
        <Callout>
          A take-home isn't a typing test. It's a writing exercise where the README is the most
          important file. Reviewers spend more time reading your docs than running your code.
        </Callout>
        <Prose>
          Use the round-length picker (top of every page) to switch between 1-day, 3-day, 1-week,
          and 2-week views. The phase below will update to match your selected budget. Each phase
          label shows the calendar slice it maps to — not minutes.
        </Prose>
      </Section>

      <Section
        key={activePlan.presetId}
        eyebrow={activePlan.label}
        title={`${activePlan.label} plan`}
        lede={`A ${activePlan.label} take-home has enough time to do the job well — but only if you sequence it correctly. Scope and prove first, build second, document last.`}
      >
        <TimelineStrip
          phases={activePlan.phases.map((phase) => ({
            id: phase.id,
            label: phase.label,
            caption: phase.timeLabel,
            body: <span>{phase.do}</span>,
          }))}
          caption={activePlan.label}
        />
        <Pact>What slips first: {activePlan.whatSlipsFirst}</Pact>
      </Section>

      <Section
        title="Phase principles — any budget"
        lede="Regardless of how many days you have, these principles hold across every take-home. Violating them is more costly than running out of time."
      >
        <SubHeading>Commit early and often</SubHeading>
        <Prose>
          Your first commit should be the spike — the thinnest proof that the central concern works.
          Not a skeleton. Not a TODO. A real, running, single happy-path invocation. Everything after
          that builds on a proven foundation. Reviewers can read your commit history and see how you
          reasoned through the problem.
        </Prose>

        <SubHeading>AI is a drafting tool, not an author</SubHeading>
        <Prose>
          Use AI to scaffold boilerplate, generate test cases, and accelerate debugging. But review
          every line before it ships. You will be asked to explain any part of your submission in a
          follow-up call — "the AI wrote it" is not an acceptable answer. The README AI-usage note
          is not a disclaimer; it is evidence of your judgment.
        </Prose>

        <SubHeading>The README is the last thing you write and the first thing reviewers read</SubHeading>
        <Prose>
          Budget real time for the final pass — not five minutes at the end. The README answers
          setup, run, test, design rationale, trade-offs, and what you would do next. A reviewer
          who can answer 80% of their follow-up questions from the README alone is a reviewer who
          gives you a callback.
        </Prose>
      </Section>
    </StudyShell>
  );
}
