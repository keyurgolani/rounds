/**
 * Code Kit — interactive reference of the data-structure shelves. The
 * Language tab strip swaps the entire file tree: Python tab shows the
 * Python shelves, JS shows the JS shelves, etc. Edits persist
 * per-language while you're on the page (switching languages and
 * coming back keeps your scratch) but reset on page navigation.
 *
 * The cards beneath the editor keep the human-readable context
 * (concept chips + method blurbs) for whichever shelf the user is
 * currently viewing.
 */
import { useMemo, useState, useCallback, type RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { CodeLanguage, TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, ChipRow, Pact } from '../../shared/primitives';
import { codingContent } from '../../content/coding';
import MultiFileEditor from '../../../../components/editor/MultiFileEditor';
import { useCodeLanguage } from './useCodeLanguage';

const LANGUAGES: { key: CodeLanguage; label: string; ext: string }[] = [
  { key: 'python',     label: 'Python',     ext: 'py'   },
  { key: 'javascript', label: 'JavaScript', ext: 'js'   },
  { key: 'java',       label: 'Java',       ext: 'java' },
];

const EXT_BY_LANG: Record<CodeLanguage, string> = {
  python: 'py',
  javascript: 'js',
  java: 'java',
};

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

type Files = Record<string, string>;
type Shelf = (typeof codingContent)['codeKit']['shelves'][number];

/** Build a per-language files map. Each shelf becomes a folder; inside
 *  is exactly one file (with the language's extension). */
function buildLangFiles(shelves: readonly Shelf[], lang: CodeLanguage): Files {
  const ext = EXT_BY_LANG[lang];
  const out: Files = {};
  for (const shelf of shelves) {
    out[`${shelf.id}/${shelf.id}.${ext}`] = shelf.implementations[lang];
  }
  return out;
}

function initialActivePath(shelf: Shelf, lang: CodeLanguage): string {
  return `${shelf.id}/${shelf.id}.${EXT_BY_LANG[lang]}`;
}

export default function CodeKit({ config, navGroups, scrollRef }: Props) {
  const { codeKit, dashboard } = codingContent;
  const [language, setLanguage] = useCodeLanguage();

  // Three independent files maps + active paths — switching languages
  // swaps the whole editor surface. Each is seeded from the static
  // starter content lazily on first render so we don't burn through
  // memory for languages the user never opens.
  const [filesByLang, setFilesByLang] = useState<Record<CodeLanguage, Files>>(() => ({
    python: buildLangFiles(codeKit.shelves, 'python'),
    javascript: buildLangFiles(codeKit.shelves, 'javascript'),
    java: buildLangFiles(codeKit.shelves, 'java'),
  }));
  const [activeByLang, setActiveByLang] = useState<Record<CodeLanguage, string>>(() => ({
    python: initialActivePath(codeKit.shelves[0], 'python'),
    javascript: initialActivePath(codeKit.shelves[0], 'javascript'),
    java: initialActivePath(codeKit.shelves[0], 'java'),
  }));

  const files = filesByLang[language];
  const activePath = activeByLang[language];

  const onPickFile = useCallback(
    (path: string) => {
      setActiveByLang((prev) => ({ ...prev, [language]: path }));
    },
    [language],
  );

  const onFileChange = useCallback(
    (path: string, contents: string) => {
      setFilesByLang((prev) => ({
        ...prev,
        [language]: { ...prev[language], [path]: contents },
      }));
    },
    [language],
  );

  const onResetFiles = useCallback(() => {
    setFilesByLang((prev) => ({
      ...prev,
      [language]: buildLangFiles(codeKit.shelves, language),
    }));
  }, [codeKit.shelves, language]);

  // Derive the currently-focused shelf from the active path so the
  // glossary below the editor matches what's on screen.
  const activeShelfId = activePath.split('/')[0];
  const activeShelf = useMemo(
    () => codeKit.shelves.find((s) => s.id === activeShelfId) ?? codeKit.shelves[0],
    [codeKit.shelves, activeShelfId],
  );

  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Code Kit`}
      title="Batteries-included Code Kit"
      description="Readable Python, JavaScript, and Java implementations grouped by data structure. Scratch in the editor — your edits stay until you leave the page."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Pact>{dashboard.codeStylePact}</Pact>

      <LanguageTabs language={language} onChange={setLanguage} />

      <div
        className="card"
        style={{
          padding: 0,
          overflow: 'hidden',
          height: 520,
        }}
      >
        <MultiFileEditor
          files={files}
          activePath={activePath}
          onActivePathChange={onPickFile}
          onFileChange={onFileChange}
          onResetFiles={onResetFiles}
          storageKey={`rounds:guide:coding:code-kit:${language}`}
        />
      </div>

      <Section
        id={activeShelf.id}
        eyebrow={`Shelf ${activeShelf.number} · ${activeShelf.name}`}
        title={activeShelf.name}
      >
        <ChipRow chips={activeShelf.concepts} />
        <div
          className="grid"
          style={{ gap: 'var(--gap-sm)', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))' }}
        >
          {activeShelf.methods.map((method) => (
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
      </Section>
    </StudyShell>
  );
}

function LanguageTabs({
  language,
  onChange,
}: {
  language: CodeLanguage;
  onChange: (next: CodeLanguage) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Language"
      style={{
        display: 'flex',
        gap: 0,
        borderBottom: '1px solid var(--border)',
      }}
    >
      {LANGUAGES.map((option) => {
        const active = language === option.key;
        return (
          <button
            key={option.key}
            type="button"
            role="tab"
            aria-selected={active}
            aria-pressed={active}
            onClick={() => onChange(option.key)}
            style={{
              padding: '10px 14px',
              fontSize: 13,
              fontWeight: 600,
              color: active ? 'var(--text)' : 'var(--text-3)',
              background: 'transparent',
              border: 0,
              borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
              marginBottom: -1,
              cursor: 'pointer',
            }}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
