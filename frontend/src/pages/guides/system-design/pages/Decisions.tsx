import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Prose, Callout, SubHeading } from '../../shared/primitives';
import { systemDesignContent } from '../../content/systemDesign';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function Decisions({ config, navGroups, scrollRef }: Props) {
  const { decisions } = systemDesignContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Decisions`}
      title="The six recurring choices"
      description="Most system design rounds turn on a small set of architectural decisions. Each one below is a choice you should be able to make confidently and defend with concrete signals."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        title="Use these to push back on your own design"
        lede="When you propose a component on the whiteboard, an interviewer is silently asking 'why this and not the obvious alternative?' These six decisions cover the recurring forks. The goal isn't to memorise the answer — it's to be able to read the prompt's signals and pick the right side, then name the trade-off out loud."
      >
        <Callout>
          A decision without a trade-off is a wish. Name the cost of the option
          you chose, every time.
        </Callout>
      </Section>

      <div className="grid" style={{ gap: 'var(--gap-lg)' }}>
        {decisions.map((topic) => (
          <DecisionCard key={topic.id} topic={topic} />
        ))}
      </div>
    </StudyShell>
  );
}

function DecisionCard({ topic }: { topic: typeof systemDesignContent.decisions[number] }) {
  return (
    <article
      id={topic.id}
      className="card"
      style={{
        padding: 'var(--pad-md)',
        display: 'grid',
        gap: 'var(--gap-md)',
        scrollMarginTop: 24,
      }}
    >
      <header className="grid" style={{ gap: 6 }}>
        <h2
          style={{
            margin: 0,
            fontSize: 'clamp(18px, 2vw, 22px)',
            lineHeight: 1.2,
            fontWeight: 600,
            color: 'var(--text)',
          }}
        >
          {topic.title}
        </h2>
        <Prose>{topic.question}</Prose>
      </header>

      <div
        className="grid"
        style={{
          gap: 'var(--gap-md)',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        }}
      >
        <OptionPanel
          eyebrow="Lean toward"
          option={topic.pickA.option}
          signals={topic.pickA.signals}
        />
        <OptionPanel
          eyebrow="Lean toward"
          option={topic.pickB.option}
          signals={topic.pickB.signals}
        />
      </div>

      <div className="grid" style={{ gap: 'var(--gap-sm)' }}>
        <SubHeading>Default when in doubt</SubHeading>
        <Prose>{topic.defaultPick}</Prose>
      </div>

      <div className="grid" style={{ gap: 'var(--gap-sm)' }}>
        <SubHeading>What to say out loud</SubHeading>
        <Prose>{topic.seniorMove}</Prose>
      </div>
    </article>
  );
}

function OptionPanel({
  eyebrow,
  option,
  signals,
}: {
  eyebrow: string;
  option: string;
  signals: string[];
}) {
  return (
    <div
      className="card"
      style={{
        padding: 'var(--pad-md)',
        background: 'var(--bg-sunken)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
        display: 'grid',
        gap: 'var(--gap-sm)',
      }}
    >
      <div
        className="mono uppercase"
        style={{ fontSize: 10.5, letterSpacing: '0.12em', color: 'var(--text-4)' }}
      >
        {eyebrow}
      </div>
      <strong style={{ fontSize: 14.5, color: 'var(--text)', fontWeight: 600 }}>
        {option}
      </strong>
      <ul
        style={{
          margin: 0,
          paddingLeft: 18,
          color: 'var(--text-2)',
          fontSize: 13.5,
          lineHeight: 1.55,
        }}
      >
        {signals.map((signal) => (
          <li key={signal} style={{ marginBottom: 4 }}>
            {signal}
          </li>
        ))}
      </ul>
    </div>
  );
}
