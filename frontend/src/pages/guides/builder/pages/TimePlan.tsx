import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Pact } from '../../shared/primitives';
import TimelineStrip from '../../shared/visuals/TimelineStrip';
import { builderContent } from '../../content/builder';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function TimePlan({ config, navGroups, scrollRef }: Props) {
  const { timePlan } = builderContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Time Plan`}
      title="Time Plans"
      description="Round-by-round budgets for 60 / 90 / 120 / 180-minute take-homes."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      {timePlan.plans.map((plan) => (
        <Section
          key={plan.totalMinutes}
          eyebrow="Plan"
          title={`${plan.totalMinutes}-minute plan`}
        >
          <TimelineStrip
            phases={plan.phases.map((phase) => ({
              id: phase.id,
              label: phase.label,
              caption: `${phase.minutes} min`,
              body: <span>{phase.do}</span>,
            }))}
            caption={`${plan.totalMinutes} min`}
          />
          <Pact>What slips first: {plan.whatSlipsFirst}</Pact>
        </Section>
      ))}
    </StudyShell>
  );
}
