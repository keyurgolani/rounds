import type { RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { CodeLanguage, TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, ChipRow, Pact } from '../../shared/primitives';
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

export default function CodeKit({ config, navGroups, scrollRef }: Props) {
  const { codeKit, dashboard } = codingContent;
  const [language, setLanguage] = useCodeLanguage();

  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Code Kit`}
      title="Batteries-included Code Kit"
      description="Readable Python, JavaScript, and Java implementations grouped by data structure. The interviewer should follow the code aloud."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
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

      <Pact>{dashboard.codeStylePact}</Pact>

      <div className="grid" style={{ gap: 'var(--gap-lg)' }}>
        {codeKit.shelves.map((shelf) => (
          <Section
            key={shelf.id}
            id={shelf.id}
            eyebrow={`Shelf ${shelf.number} · ${shelf.name}`}
            title={shelf.name}
          >
            <ChipRow chips={shelf.concepts} />
            <div
              className="grid"
              style={{ gap: 'var(--gap-sm)', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))' }}
            >
              {shelf.methods.map((method) => (
                <div
                  key={method.name}
                  className="card"
                  style={{ padding: 'var(--pad-sm)' }}
                >
                  <strong className="mono" style={{ fontSize: 12.5, color: 'var(--accent)' }}>{method.name}</strong>
                  <p style={{ margin: '4px 0 0', color: 'var(--text-3)', fontSize: 12.5, lineHeight: 1.45 }}>
                    {method.purpose}
                  </p>
                </div>
              ))}
            </div>
            <pre
              style={{
                margin: 0,
                padding: 'var(--pad-md)',
                borderRadius: 'var(--radius)',
                background: 'var(--bg-sunken)',
                boxShadow: 'inset 0 0 0 1px var(--border)',
                color: 'var(--text-2)',
                fontSize: 12.5,
                lineHeight: 1.55,
                overflowX: 'auto',
              }}
            >
              <code>{shelf.implementations[language]}</code>
            </pre>
          </Section>
        ))}
      </div>
    </StudyShell>
  );
}
