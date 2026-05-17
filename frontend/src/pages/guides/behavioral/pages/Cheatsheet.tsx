import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, GuidanceGrid, Guidance, LaneCard } from '../../shared/primitives';
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
      <Section
        eyebrow="Pre-flight"
        title="What an answer must prove"
        lede="Before you start any story, run a quick mental check: does this answer show each of the six dimensions below? Missing even one — especially judgment or outcome — drops the score by a full band. The checklist is designed to take under 10 seconds during the 5–10 second pause you take before answering."
      >
        <GuidanceGrid>
          <Guidance label="Trait">
            Name the signal explicitly in your opening line so the interviewer knows which competency your story targets. Don't make them guess.
          </Guidance>
          <Guidance label="Context">
            Give the minimum viable situation — stakes, constraint, and your role — in 15 seconds or less. Longer setup crowds out Action, which is where you're actually scored.
          </Guidance>
          <Guidance label="Action">
            This is the score-determining segment. State the specific decisions you made, the trade-offs you weighed, and the communication steps you took — in the first person, with verbs.
          </Guidance>
          <Guidance label="Judgment">
            Name the criteria you used to choose one path over another. "I prioritized reliability over speed because the rollback cost would have been 3x the delay" scores higher than "we decided to go slow."
          </Guidance>
          <Guidance label="Outcome">
            Close with a quantified result and a secondary effect. The secondary effect — what changed durably, not just in this instance — is where senior scores separate from mid-level scores.
          </Guidance>
          <Guidance label="Learning">
            End with what updated in your operating model and where you applied it later. Generic lessons ("I learned communication matters") score as 1 of 3; behavior-proof lessons score as 3 of 3.
          </Guidance>
        </GuidanceGrid>
      </Section>

      <Section
        eyebrow="Question Deck"
        title="Eight openers — match the signal, run the move"
        lede="Each card pairs an opener you'll hear with the underlying signal being tested, the move that scores well, and the watch item — the failure mode that tanks otherwise-good stories. Use this during prep: for each opener, drill the move until the response is reflexive, not constructed."
      >
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

      <Section
        eyebrow="Red Flags"
        title="Replacements that move the answer up a level"
        lede="Weak answers don't fail because candidates pick the wrong story — they fail because of execution patterns that experienced interviewers recognize instantly. The fixes below are surgical: each replaces a habit that signals low awareness with one that signals high precision."
      >
        <GuidanceGrid>
          <Guidance label="Replace blame with ownership">
            When something went wrong, begin with your own bad assumption or missed signal before describing external factors. Interviewers expect imperfection; they're scoring whether you own your part.
          </Guidance>
          <Guidance label='Replace vague "we" with clear "I"'>
            "We shipped the feature" tells the interviewer nothing about your contribution. Say what you specifically decided, built, or drove — then credit the team for shared outcomes afterward.
          </Guidance>
          <Guidance label="Add numbers">
            Quantify the result, the scope, or the timeline. Even rough numbers ("roughly 30% reduction", "across 4 teams", "over 6 weeks") are vastly more credible than qualitative claims.
          </Guidance>
          <Guidance label="Cut setup">
            Most candidates spend 60–90 seconds on Situation when 15 seconds is optimal. If you catch yourself explaining organizational history, you're in the wrong part of the story.
          </Guidance>
          <Guidance label="Name the trade-off">
            Every good decision involves a trade-off. State what you gave up and why the cost was acceptable. Decisions that look optimal in hindsight are suspicious; decisions with articulated trade-offs are credible.
          </Guidance>
          <Guidance label="Include reflection">
            End with what you would do differently or where you applied the learning. A story without reflection closes at Result, which is only 4 of the 5 STAR(R) segments — and misses the senior differentiator.
          </Guidance>
          <Guidance label="Show follow-up behavior">
            Prove the learning was real by citing a later situation where you applied it. "I now send written decision logs before cross-team reviews" is proof; "I learned to communicate better" is not.
          </Guidance>
        </GuidanceGrid>
      </Section>
    </StudyShell>
  );
}
