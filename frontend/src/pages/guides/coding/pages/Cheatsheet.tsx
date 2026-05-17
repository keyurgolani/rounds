import { useState, type RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { PatternFamily, TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, ChipRow, LaneCard, Prose } from '../../shared/primitives';
import { codingContent } from '../../content/coding';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

const FAMILY_FILTERS: { key: PatternFamily | 'all'; label: string }[] = [
  { key: 'all',          label: 'All' },
  { key: 'linear',       label: 'Linear' },
  { key: 'search',       label: 'Search' },
  { key: 'graph',        label: 'Graph' },
  { key: 'dp',           label: 'DP' },
  { key: 'backtracking', label: 'Backtracking' },
  { key: 'stack-heap',   label: 'Stack / Heap' },
];

export default function Cheatsheet({ config, navGroups, scrollRef }: Props) {
  const { cheatsheet } = codingContent;
  const [filter, setFilter] = useState<PatternFamily | 'all'>('all');
  const visibleRows = filter === 'all'
    ? cheatsheet.patternMatrix
    : cheatsheet.patternMatrix.filter((row) => row.family === filter);

  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Cheatsheet`}
      title="Coding Cheatsheet"
      description="Trigger → state → move → watch for. Use this when a problem lands and you need a fast pattern-to-plan translation."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        title="Before you code"
        lede="The biggest interview mistakes happen in the first two minutes — jumping to code before the problem is understood. Run through this checklist out loud. It takes thirty seconds and prevents the worst kind of backtrack: realising mid-solution that you misread the constraints."
      >
        <Prose size="sm">Each item below is a question to ask or a check to make before your fingers hit the keyboard. Don't internalize these as rules; use them as a spoken script that signals structured thinking to the interviewer.</Prose>
        <ChipRow chips={cheatsheet.preflight} />
      </Section>

      <Section
        title="What constraints allow"
        lede="Each line below is a rule of thumb: given this input size, your solution must fit inside this complexity class. Scan the constraint in the problem first, pick the matching row, and let it rule out whole families of algorithms before you sketch anything."
      >
        <div
          className="grid"
          style={{ gap: 'var(--gap-sm)', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}
        >
          {cheatsheet.complexityCeiling.map((line) => (
            <div
              key={line}
              className="mono"
              style={{
                padding: 'var(--pad-sm)',
                borderRadius: 'var(--radius)',
                background: 'var(--bg-elev)',
                boxShadow: 'inset 0 0 0 1px var(--border)',
                color: 'var(--text-2)',
                fontSize: 12,
              }}
            >
              {line}
            </div>
          ))}
        </div>
      </Section>

      <Section
        eyebrow="Pattern Matrix"
        title="Recognize the pattern → know the move"
        lede="Pattern recognition is the core interview skill. Each card maps a trigger phrase — the kind of language the problem uses — to the state you'd declare and the exact move you'd make. Filter by family to focus on one algorithm class at a time."
      >
        <div className="flex flex-wrap" style={{ gap: 'var(--gap-sm)' }}>
          {FAMILY_FILTERS.map((option) => {
            const active = option.key === filter;
            return (
              <button
                key={option.key}
                type="button"
                onClick={() => setFilter(option.key)}
                className="pill"
                style={{
                  background: active ? 'var(--accent-soft)' : 'var(--bg-elev)',
                  color: active ? 'var(--accent)' : 'var(--text-2)',
                  boxShadow: `inset 0 0 0 1px ${active ? 'var(--accent)' : 'var(--border)'}`,
                  border: 0,
                  cursor: 'pointer',
                  fontSize: 11.5,
                }}
              >
                {option.label}
              </button>
            );
          })}
        </div>
        <div
          className="grid"
          style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}
        >
          {visibleRows.map((row) => (
            <LaneCard
              key={row.id}
              eyebrow={row.family.toUpperCase()}
              title={row.trigger}
              body={
                <div className="grid" style={{ gap: 6 }}>
                  <span><strong style={{ color: 'var(--text-2)' }}>State:</strong> {row.state}</span>
                  <span><strong style={{ color: 'var(--text-2)' }}>Move:</strong> {row.move}</span>
                </div>
              }
              footer={`Watch: ${row.watch}`}
            />
          ))}
        </div>
      </Section>
    </StudyShell>
  );
}
