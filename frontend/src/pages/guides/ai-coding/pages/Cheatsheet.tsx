import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig, AIFlavor } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Prose, Guidance, GuidanceGrid } from '../../shared/primitives';
import DecisionDeck from '../../shared/visuals/DecisionDeck';
import { aiCodingContent } from '../../content/aiCoding';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

function prettyLabel(id: AIFlavor): string {
  const map: Record<AIFlavor, string> = {
    'audit': 'Audit',
    'drive': 'Drive',
    'debug-refactor': 'Debug-Refactor',
    'prompt-spec': 'Prompt-Spec',
    'mini-app': 'Mini-app',
  };
  return map[id] ?? id;
}

export default function Cheatsheet({ config, navGroups, scrollRef }: Props) {
  const { cheatsheet } = aiCodingContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Cheatsheet`}
      title="AI Coding Cheatsheet"
      description="Policy mode, flavor move, red flag — at a glance."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        title="What the AI policy means"
        lede="Every AI-assisted round starts with a policy declaration. Getting it wrong in either direction — using AI when you shouldn't, or not using it when you should — sets the wrong tone immediately. Read the policy carefully, confirm it with the interviewer if unclear, then lock it in before writing a single line."
      >
        <GuidanceGrid>
          {cheatsheet.policyModes.map((mode) => (
            <Guidance key={mode.mode} label={mode.mode.toUpperCase()}>
              <strong>When:</strong> {mode.when}<br />
              <strong>Expectation:</strong> {mode.expectation}
            </Guidance>
          ))}
        </GuidanceGrid>
      </Section>

      <Section
        title="Pick the right move for the flavor"
        lede="Each round flavor has a dominant move — the action that earns the most signal — and a common trap. Identifying which flavor you're in within the first two minutes lets you allocate your time correctly and avoid the trap that catches most candidates."
      >
        <DecisionDeck
          entries={cheatsheet.flavorDeck.map((card) => ({
            id: card.id,
            eyebrow: prettyLabel(card.id),
            trigger: card.trigger,
            move: card.move,
            watch: card.watch,
          }))}
        />
      </Section>

      <Section
        title="Red-flag pile"
        lede="These are the behaviors that immediately signal to an interviewer that a candidate is not reviewing AI output — they're using it as a black box. Any one of these can flip a hire to a no-hire regardless of what the code does."
      >
        <div className="grid" style={{ gap: 'var(--gap-md)' }}>
          {cheatsheet.redFlags.map((flag) => (
            <div
              key={flag}
              className="card"
              style={{
                padding: 'var(--pad-md)',
                background: 'var(--bg-elev)',
                boxShadow: 'inset 0 0 0 1px var(--border)',
              }}
            >
              <Prose size="sm">{flag}</Prose>
            </div>
          ))}
        </div>
      </Section>
    </StudyShell>
  );
}
