import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import {
  Section,
  Callout,
  Prose,
  Pact,
  GuidanceGrid,
  Guidance,
} from '../../shared/primitives';
import { builderContent } from '../../content/builder';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function Submission({ config, navGroups, scrollRef }: Props) {
  const { submission } = builderContent;
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Submission`}
      title="Submission"
      description="README template, commit hygiene, what reviewers check first."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        title="The README is your interview transcript"
        lede="A take-home isn't a typing test — it's a writing exercise where the README is the most important file. Reviewers spend more time reading your docs than running your code. Treat the README as your one-page interview transcript: it should pre-empt 80% of the follow-up questions a reviewer would otherwise ask on a call."
      >
        <Callout>
          Submission quality matters more than novelty. A working app with a clean README that
          explains trade-offs beats a fancier app with poor docs — every time.
        </Callout>
        <Prose>
          The five things a reviewer does in their first five minutes: clone, run, read the README,
          read the git log, scan one interesting file. Your submission should pass all five without
          any help from you. If they have to email you to ask how to run it, the first impression
          is already damaged.
        </Prose>
      </Section>

      <Section
        eyebrow="README"
        title="Copyable scaffold"
        lede="Use this structure directly. Each section exists because reviewers ask exactly these questions in follow-up calls. A section left blank is a question you are forcing them to ask out loud."
      >
        <pre
          className="mono"
          style={{
            margin: 0,
            padding: 'var(--pad-md)',
            background: 'var(--bg-sunken)',
            borderRadius: 'var(--radius)',
            boxShadow: 'inset 0 0 0 1px var(--border)',
            color: 'var(--text-2)',
            fontSize: 12,
            lineHeight: 1.55,
            overflowX: 'auto',
            whiteSpace: 'pre',
          }}
        >{submission.readmeTemplate}</pre>
      </Section>

      <Section
        eyebrow="Commits"
        title="How your git log should read"
        lede="Your commit history is a second README. Reviewers use it to understand how you reasoned through the problem — not just what you built, but in what order and why. A single 'initial commit' with 500 changed files tells them nothing. A commit-per-feature story tells them everything."
      >
        <Pact>
          <ul style={{ margin: 0, paddingLeft: 20, display: 'grid', gap: 8 }}>
            {submission.commitHygiene.map((line) => (
              <li key={line} style={{ lineHeight: 1.6 }}>{line}</li>
            ))}
          </ul>
        </Pact>
      </Section>

      <Section
        eyebrow="AI Usage"
        title="Acknowledging AI in your submission"
        lede="Reviewers know you used AI. The question is whether you owned the output. A brief AI-usage note in the README transforms a potential liability into a signal of transparency and judgment."
      >
        <GuidanceGrid>
          <Guidance label="What to say">
            A single paragraph is enough: which parts were AI-assisted, what you reviewed, and what
            you rewrote or verified manually. 'I used AI to scaffold the CSV parser and the test
            fixtures. I rewrote the retry loop by hand after the generated version had a race
            condition I caught in review.'
          </Guidance>
          <Guidance label="What not to say">
            Do not disclaim everything vaguely ('AI was used throughout'). Do not claim you wrote
            everything manually if you did not — reviewers can tell. The goal is specificity, not
            a legal disclaimer.
          </Guidance>
          <Guidance label="Optional: Loom walkthrough">
            A 5-minute screen recording showing the app running and explaining one design decision
            out loud sets the right tone — even when not explicitly requested. It demonstrates that
            you understand what you built and can communicate about it clearly.
          </Guidance>
        </GuidanceGrid>
      </Section>

      <Section
        eyebrow="Review"
        title="The 5 things reviewers grade first"
        lede="Before they read a single line of your implementation, reviewers run through this checklist. It takes them under 5 minutes. Make sure your submission passes before you push."
      >
        <Pact>
          <ol style={{ margin: 0, paddingLeft: 20, display: 'grid', gap: 8 }}>
            {submission.reviewerFirstPass.map((line) => (
              <li key={line} style={{ lineHeight: 1.6 }}>{line}</li>
            ))}
          </ol>
        </Pact>
      </Section>
    </StudyShell>
  );
}
