import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Prose, GuidanceGrid, Guidance } from '../../shared/primitives';
import { behavioralContent } from '../../content/behavioral';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function StoryBank({ config, navGroups, scrollRef }: Props) {
  const { storyBank } = behavioralContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Story Bank`}
      title="Story Bank"
      description="Eight signals × four evidence dimensions. Build your portfolio before the loop, not during it."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        eyebrow="Portfolio"
        title="What good evidence looks like for each signal"
        lede="Each card below is a signal the interviewer wants to confirm. The four dimensions — artifacts, metrics, stakeholders, and criteria — are the ingredients that make a story credible. Before your interview, check that your stored anecdote for each signal includes at least one artifact and one metric; stories without both tend to sound generic."
      >
        <div
          className="grid"
          style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}
        >
          {storyBank.signals.map((signal) => (
            <article
              key={signal.key}
              className="card"
              style={{ padding: 'var(--pad-md)', display: 'grid', gap: 'var(--gap-sm)' }}
            >
              <div className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.12em' }}>
                SIGNAL
              </div>
              <strong style={{ fontSize: 15, fontWeight: 600 }}>{signal.name}</strong>
              <DimensionList label="Artifacts"    items={signal.artifacts} />
              <DimensionList label="Metrics"      items={signal.metrics} />
              <DimensionList label="Stakeholders" items={signal.stakeholders} />
              <DimensionList label="Criteria"     items={signal.criteria} />
            </article>
          ))}
        </div>
      </Section>

      <Section
        eyebrow="Format"
        title="Canonical story entry"
        lede="This is the format to use when writing an anecdote into your library. The fields are ordered by what the interviewer needs to hear earliest — title for fast retrieval, signals for matching to questions, numbers for instant credibility, and weak spot so you're not surprised by a follow-up."
      >
        <div className="card" style={{ padding: 'var(--pad-md)' }}>
          <dl style={{ margin: 0, display: 'grid', gap: 'var(--gap-sm)' }}>
            {storyBank.storyFormat.map((row) => (
              <div key={row.field} className="grid" style={{ gridTemplateColumns: '110px 1fr', gap: 'var(--gap-sm)', alignItems: 'baseline' }}>
                <dt className="mono" style={{ fontSize: 11, color: 'var(--text-4)', letterSpacing: '0.12em' }}>
                  {row.field.toUpperCase()}
                </dt>
                <dd style={{ margin: 0, color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.55 }}>{row.example}</dd>
              </div>
            ))}
          </dl>
        </div>
      </Section>

      <Section
        eyebrow="Angles"
        title="One story → many prompts"
        lede="A well-constructed story is reusable. The same project that demonstrates impact can be told as a conflict story, a failure story, or a leadership story depending on which angle you lead with. The cards below show how to choose the lead — the first sentence determines which signal the interviewer scores."
      >
        <GuidanceGrid>
          {storyBank.reusableAngles.map((entry) => (
            <Guidance key={entry.angle} label={entry.angle}>
              {ANGLE_EXPANSIONS[entry.angle] ?? entry.lead}
            </Guidance>
          ))}
        </GuidanceGrid>
        <Prose size="sm">
          To reuse a story: pick the angle that matches the signal being asked about, restructure the first sentence to lead with that angle's framing, then proceed through STAR normally. The underlying facts stay the same — only the lens changes.
        </Prose>
      </Section>
    </StudyShell>
  );
}

const ANGLE_EXPANSIONS: Record<string, string> = {
  'Impact angle':     'Open with the metric and explain why it mattered to the business or users, before saying anything about what you did. Pull the audience into the stakes before the story.',
  'Conflict angle':   'Open with the disagreement and who held which position. Make both sides sound reasonable — then show how you built alignment through criteria, not persuasion.',
  'Failure angle':    'Open with the bad assumption you made and the impact it caused. Own it directly. Then move to repair work and the later proof that your operating model updated.',
  'Ambiguity angle':  'Open with what was missing — unclear ownership, competing requirements, or absent data. Then show the structure you created from nothing and the trade-off you made explicit.',
  'Leadership angle': 'Open with how a peer or team outside your reporting line changed their behavior because of something you built or demonstrated. Titles don\'t matter; behavior change does.',
  'Growth angle':     'Open with the specific feedback you received, including your initial emotional reaction. Then describe the behavior that changed and cite a later outcome as proof.',
};

function DimensionList({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="grid" style={{ gap: 4 }}>
      <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)', letterSpacing: '0.12em' }}>{label.toUpperCase()}</span>
      <div className="flex flex-wrap" style={{ gap: 4 }}>
        {items.map((item) => (
          <span
            key={item}
            className="pill"
            style={{
              background: 'var(--bg-sunken)',
              color: 'var(--text-2)',
              boxShadow: 'inset 0 0 0 1px var(--border)',
              fontSize: 11,
            }}
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
