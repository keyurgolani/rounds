import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, GuidanceGrid, Guidance, Pact, Prose } from '../../shared/primitives';
import { behavioralContent } from '../../content/behavioral';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function SeniorScope({ config, navGroups, scrollRef }: Props) {
  const { seniorScope } = behavioralContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Senior Scope`}
      title="Senior Scope"
      description="Show scope in numbers. Show judgment in criteria. Defend the risky interpretation."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        eyebrow="Ladder"
        title="Mid → Principal — what scope looks like at each tier"
        lede="The most common calibration failure in senior-and-above interviews is telling a mid-level story for a senior role — or a senior story that sounds staff-level to a principal panel. The ladder below shows the expected scope markers at each tier. Before your interview, audit your anecdotes: do the numbers and stakeholder span match the level you're applying for?"
      >
        <ol style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 'var(--gap-md)' }}>
          {seniorScope.ladder.map((tier, index) => (
            <li
              key={tier.level}
              className="card"
              style={{
                padding: 'var(--pad-md)',
                display: 'grid',
                gap: 'var(--gap-sm)',
                gridTemplateColumns: 'auto minmax(0, 1fr)',
                alignItems: 'start',
              }}
            >
              <span
                className="mono"
                style={{
                  width: 36, height: 36,
                  display: 'grid', placeItems: 'center',
                  borderRadius: 999,
                  background: 'var(--accent-soft)',
                  color: 'var(--accent)',
                  fontSize: 11,
                  fontWeight: 600,
                }}
              >
                T{index + 1}
              </span>
              <div className="grid" style={{ gap: 6 }}>
                <strong style={{ fontSize: 15, fontWeight: 600 }}>{tier.label}</strong>
                <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.5 }}>
                  {tier.examples.map((example) => <li key={example}>{example}</li>)}
                </ul>
                <div className="flex flex-wrap" style={{ gap: 6 }}>
                  {tier.numbers.map((number) => (
                    <span
                      key={number}
                      className="pill mono"
                      style={{
                        background: 'var(--bg-sunken)',
                        color: 'var(--text-2)',
                        boxShadow: 'inset 0 0 0 1px var(--border)',
                        fontSize: 11,
                      }}
                    >
                      {number}
                    </span>
                  ))}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <Section
        eyebrow="Frame"
        title="Six elements every senior answer has"
        lede="Senior panels aren't just scoring whether you completed something — they're scoring whether you understand why it mattered, how you navigated ambiguity, and whether your decisions would hold up to scrutiny. The six elements below are the difference between a story that answers the question and a story that signals operating maturity."
      >
        <GuidanceGrid>
          {ANSWER_FRAME_GUIDANCE.map((item) => (
            <Guidance key={item.label} label={item.label}>
              {item.body}
            </Guidance>
          ))}
        </GuidanceGrid>
        <Prose size="sm">
          For defensive framing of risky stories (escalation, failure, disagreement), see{' '}
          <strong>Mental Model → When the story has risk</strong>. The moves there apply equally
          at senior and above.
        </Prose>
      </Section>

      <Section
        eyebrow="Calibration"
        title="Audit your library for scope signals"
        lede="Once you've written your anecdote library, run a calibration pass. For each story, ask: does the stakeholder span, number of teams affected, and timeline match the level you're targeting? A strong action in a too-small context reads as mid-level regardless of quality."
      >
        <Pact>
          <ol style={{ margin: 0, paddingLeft: 18 }}>
            {CALIBRATION_STEPS.map((step) => (
              <li key={step} style={{ marginBottom: 6 }}>{step}</li>
            ))}
          </ol>
        </Pact>
      </Section>
    </StudyShell>
  );
}

const ANSWER_FRAME_GUIDANCE = [
  {
    label: 'Open with outcome',
    body: 'Lead with the result before explaining what you did. "This reduced incidents by 38% across three teams" anchors the story at the right altitude and signals that you think in outcomes, not activities.',
  },
  {
    label: 'Name the ambiguity',
    body: 'Senior interviewers expect unclear ownership, conflicting goals, or missing data. Describe what was ambiguous explicitly — it shows you can articulate a problem precisely before trying to solve it.',
  },
  {
    label: 'Name decision criteria',
    body: 'State the criteria you used to choose between options: reversibility, blast radius, cost, reliability, team morale. Criteria-driven decisions are senior signals; gut-feel decisions are not.',
  },
  {
    label: 'Show alignment mechanism',
    body: 'Describe the specific mechanism you used to get others aligned — RFC, working prototype, phased rollout, decision log. "I got buy-in" without the mechanism sounds like luck; the mechanism shows repeatability.',
  },
  {
    label: 'Show operating maturity',
    body: 'Mention the operational guardrails: observability, rollback plan, runbook, post-launch review. Senior engineers build for failure modes; demonstrating you did shows you operate at the right altitude.',
  },
  {
    label: 'End with lesson applied at larger scope',
    body: 'Close with where you reused the decision, mechanism, or lesson — and at what scale. A lesson applied once is learning; a lesson applied at increasing scope is growth.',
  },
];

const CALIBRATION_STEPS = [
  'For each anecdote, write the stakeholder count and team span in one sentence.',
  'Compare that sentence to the ladder tier above. Does it match the level you\'re applying for?',
  'If not, either find a bigger story for that signal, or add scope context that\'s currently missing from your telling.',
  'Check your numbers: revenue, users, timeline, team size. Replace "large" and "significant" with actual figures.',
  'Verify that at least two anecdotes show cross-functional alignment — not just within your team.',
];
