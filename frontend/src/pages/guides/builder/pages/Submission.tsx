import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Pact } from '../../shared/primitives';
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
      <Section eyebrow="README" title="Copyable scaffold">
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

      <Section eyebrow="Commits" title="How your git log should read">
        <Pact>
          <ul style={{ margin: 0, paddingLeft: 20, display: 'grid', gap: 8 }}>
            {submission.commitHygiene.map((line) => (
              <li key={line} style={{ lineHeight: 1.6 }}>{line}</li>
            ))}
          </ul>
        </Pact>
      </Section>

      <Section eyebrow="Review" title="The 5 things reviewers grade first">
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
