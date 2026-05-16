import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, LaneCard } from '../../shared/primitives';
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
      <Section eyebrow="Primers" title="Domain primers for recurring shapes">
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
