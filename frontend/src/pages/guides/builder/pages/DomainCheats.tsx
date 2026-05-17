import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Callout, LaneCard, Prose } from '../../shared/primitives';
import { builderContent } from '../../content/builder';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function DomainCheats({ config, navGroups, scrollRef }: Props) {
  const { domainCheats } = builderContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Domain Cheats`}
      title="Domain Cheats"
      description="Common domain primers — entities, operations, traps."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        title="Domain primers for recurring shapes"
        lede="When the prompt is in one of these domains, these are the standard concerns reviewers look for. Use this as a checklist before submission, not a script. Each primer names the core entities and operations, and — most importantly — the one trap that causes silent failures in that domain."
      >
        <Prose>
          Take-home reviewers have seen hundreds of submissions in each of these domains. They know
          exactly which invariant most candidates miss, and they test it explicitly. Reading the
          relevant primer before you finalize your data model takes two minutes and regularly
          catches a load-bearing edge case before it becomes a silent failure in the test suite.
        </Prose>
        <Callout>
          Every domain has one load-bearing rule. Find it in the prompt, write a test for it first,
          and make sure your model preserves it under every operation.
        </Callout>
      </Section>

      <Section
        eyebrow="Primers"
        title="Reference by domain"
        lede="Each card shows the minimal domain model (entities, operations, and evaluation order) plus the single trap that almost always shows up in hidden tests."
      >
        <div
          className="grid"
          style={{
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 'var(--gap-md)',
          }}
        >
          {domainCheats.primers.map((primer) => (
            <LaneCard
              key={primer.id}
              eyebrow={primer.domain}
              title="Model"
              body={
                <pre
                  className="mono"
                  style={{
                    margin: 0,
                    padding: 'var(--pad-sm)',
                    background: 'var(--bg-sunken)',
                    borderRadius: 'var(--radius)',
                    boxShadow: 'inset 0 0 0 1px var(--border)',
                    color: 'var(--text-2)',
                    fontSize: 11.5,
                    lineHeight: 1.55,
                    whiteSpace: 'pre',
                    overflowX: 'auto',
                  }}
                >{primer.model}</pre>
              }
              footer={
                <span>
                  <strong style={{ color: 'var(--text-3)' }}>Trap:</strong> {primer.trap}
                </span>
              }
            />
          ))}
        </div>
      </Section>
    </StudyShell>
  );
}
