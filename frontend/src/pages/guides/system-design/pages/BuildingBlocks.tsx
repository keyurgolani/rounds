import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section } from '../../shared/primitives';
import DecisionDeck from '../../shared/visuals/DecisionDeck';
import { systemDesignContent } from '../../content/systemDesign';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function BuildingBlocks({ config, navGroups, scrollRef }: Props) {
  const { buildingBlocks } = systemDesignContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Building Blocks`}
      title="Building Blocks"
      description="The components and storage choices that recur — every box on your board lives in here."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Components" title="Decision blocks for the boxes on your board">
        <DecisionDeck entries={buildingBlocks.components} />
      </Section>

      <Section eyebrow="Storage" title="Pick storage from access pattern, not fashion">
        <div className="card" style={{ padding: 'var(--pad-md)', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>Kind</th>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>Use when</th>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>Primary key shape</th>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>Trade-off named</th>
              </tr>
            </thead>
            <tbody>
              {buildingBlocks.storage.map((row) => (
                <tr key={row.kind} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: 8, color: 'var(--text-2)', fontWeight: 500 }}>{row.kind}</td>
                  <td style={{ padding: 8, color: 'var(--text-3)' }}>{row.useWhen}</td>
                  <td style={{ padding: 8, color: 'var(--text-3)' }}>{row.primaryKeyShape}</td>
                  <td style={{ padding: 8, color: 'var(--text-3)' }}>{row.tradeOffNamed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section eyebrow="Keys & Indexes" title="What to say out loud about every entity">
        <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.65 }}>
          {buildingBlocks.keysIndexesNotes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </Section>

      <Section eyebrow="Sharding & Consistency" title="The conversation that wins senior signal">
        <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.65 }}>
          {buildingBlocks.shardingNotes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </Section>
    </StudyShell>
  );
}
