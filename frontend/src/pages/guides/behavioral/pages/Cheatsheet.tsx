import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, ChipRow, LaneCard } from '../../shared/primitives';
import { behavioralContent } from '../../content/behavioral';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function Cheatsheet({ config, navGroups, scrollRef }: Props) {
  const { cheatsheet } = behavioralContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Cheatsheet`}
      title="Behavioral Cheatsheet"
      description="Question type → signal → move → watch. The deck you keep open during a behavioral loop."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="STAR(R)" title="Time-budget reminder">
        <div className="flex flex-wrap" style={{ gap: 'var(--gap-sm)' }}>
          {cheatsheet.starStrip.map((segment) => (
            <span
              key={segment.id}
              className="pill"
              style={{
                background: 'var(--accent-soft)',
                color: 'var(--accent)',
                boxShadow: 'none',
                fontSize: 11.5,
                fontWeight: 600,
              }}
            >
              {segment.label} · {segment.seconds}
            </span>
          ))}
        </div>
      </Section>

      <Section eyebrow="Pre-flight" title="What an answer must prove">
        <ChipRow chips={cheatsheet.preflight} />
      </Section>

      <Section eyebrow="Question Deck" title="Eight openers — match the signal, run the move">
        <div
          className="grid"
          style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}
        >
          {cheatsheet.questionDeck.map((entry) => (
            <LaneCard
              key={entry.id}
              eyebrow={`Signal · ${entry.signal}`}
              title={entry.trigger}
              body={<span><strong style={{ color: 'var(--text-2)' }}>Move:</strong> {entry.move}</span>}
              footer={`Watch: ${entry.watch}`}
            />
          ))}
        </div>
      </Section>

      <Section eyebrow="Red Flags" title="Replacements that move the answer up a level">
        <ChipRow chips={cheatsheet.redFlagFixes} />
      </Section>
    </StudyShell>
  );
}
