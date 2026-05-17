import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { CodeLanguage, TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Prose } from '../../shared/primitives';
import { codingContent } from '../../content/coding';
import { useCodeLanguage } from './useCodeLanguage';

const LANGUAGES: { key: CodeLanguage; label: string }[] = [
  { key: 'python',     label: 'Python' },
  { key: 'javascript', label: 'JavaScript' },
  { key: 'java',       label: 'Java' },
];

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function Patterns({ config, navGroups, scrollRef }: Props) {
  const { patterns } = codingContent;
  const [language, setLanguage] = useCodeLanguage();
  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Patterns`}
      title="Pattern Playbook"
      description="A library of patterns with templates in Python, JavaScript, and Java. Match a trigger, copy the template, name the invariant."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        title="Pattern templates by language"
        lede="Each card pairs a problem trigger with the exact state variable to declare and the skeleton code you'd write. Pick your language, scan the 'When' line to identify the pattern, then use the template as your starting scaffold — fill in variable names before you start coding logic."
      >
        <div className="flex flex-wrap" style={{ gap: 'var(--gap-sm)', alignItems: 'center' }}>
          <span className="eyebrow">Language</span>
          <div className="flex" style={{ gap: 4 }}>
            {LANGUAGES.map((option) => {
              const active = language === option.key;
              return (
                <button
                  key={option.key}
                  type="button"
                  onClick={() => setLanguage(option.key)}
                  aria-pressed={active}
                  className="pill"
                  style={{
                    border: 0,
                    cursor: 'pointer',
                    background: active ? 'var(--accent-soft)' : 'var(--bg-elev)',
                    color: active ? 'var(--accent)' : 'var(--text-2)',
                    boxShadow: `inset 0 0 0 1px ${active ? 'var(--accent)' : 'var(--border)'}`,
                    fontSize: 11.5,
                  }}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        </div>

        <Prose size="sm">
          Read the <strong>Watch</strong> line before you start coding — it flags the single most common mistake for each pattern and saves you from discovering it mid-interview.
        </Prose>

        <div
          className="grid"
          style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))' }}
        >
          {patterns.entries.map((entry) => (
            <article
              key={entry.id}
              className="card"
              style={{ padding: 'var(--pad-md)', display: 'grid', gap: 'var(--gap-sm)' }}
            >
              <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.12em' }}>
                {entry.family.toUpperCase()}
              </span>
              <strong style={{ fontSize: 15, fontWeight: 600 }}>{entry.title}</strong>
              <p style={{ margin: 0, color: 'var(--text-3)', fontSize: 12.5, lineHeight: 1.45 }}>
                <strong style={{ color: 'var(--text-2)' }}>When:</strong> {entry.trigger}
              </p>
              <p style={{ margin: 0, color: 'var(--text-3)', fontSize: 12.5, lineHeight: 1.45 }}>
                <strong style={{ color: 'var(--text-2)' }}>State:</strong> {entry.state}
              </p>
              <pre
                style={{
                  margin: 0,
                  padding: '10px 14px',
                  borderRadius: 'var(--radius)',
                  background: 'var(--bg-sunken)',
                  boxShadow: 'inset 0 0 0 1px var(--border)',
                  color: 'var(--text-2)',
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: 12.5,
                  lineHeight: 1.65,
                  overflowX: 'auto',
                  whiteSpace: 'pre',
                }}
              >
                <code>{entry.skeletons[language]}</code>
              </pre>
              <p style={{ margin: 0, color: 'var(--text-4)', fontSize: 12, lineHeight: 1.45 }}>
                Watch: {entry.watch}
              </p>
            </article>
          ))}
        </div>
      </Section>
    </StudyShell>
  );
}
