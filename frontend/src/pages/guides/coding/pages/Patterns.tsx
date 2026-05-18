/**
 * Pattern Playbook — interactive reference of pattern skeletons. The
 * Language tab strip swaps the entire file tree: Python tab shows the
 * Python skeletons, JS shows the JS skeletons, etc. Edits persist
 * per-language while you're on the page but reset on page navigation.
 */
import { useMemo, useState, useCallback, type RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { CodeLanguage, TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, Prose } from '../../shared/primitives';
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
type PatternEntry = (typeof codingContent)['patterns']['entries'][number];

/** Strip the `pat-` prefix so the path reads cleanly in the file tree. */
function folderFor(entry: PatternEntry): string {
  return entry.id.replace(/^pat-/, '');
}

function buildLangFiles(entries: readonly PatternEntry[], lang: CodeLanguage): Files {
  const ext = EXT_BY_LANG[lang];
  const out: Files = {};
  for (const entry of entries) {
    const folder = folderFor(entry);
    out[`${folder}/${folder}.${ext}`] = entry.skeletons[lang];
  }
  return out;
}

function initialActivePath(entry: PatternEntry, lang: CodeLanguage): string {
  const folder = folderFor(entry);
  return `${folder}/${folder}.${EXT_BY_LANG[lang]}`;
}

export default function Patterns({ config, navGroups, scrollRef }: Props) {
  const { patterns } = codingContent;
  const [language, setLanguage] = useCodeLanguage();

  const [filesByLang, setFilesByLang] = useState<Record<CodeLanguage, Files>>(() => ({
    python: buildLangFiles(patterns.entries, 'python'),
    javascript: buildLangFiles(patterns.entries, 'javascript'),
    java: buildLangFiles(patterns.entries, 'java'),
  }));
  const [activeByLang, setActiveByLang] = useState<Record<CodeLanguage, string>>(() => ({
    python: initialActivePath(patterns.entries[0], 'python'),
    javascript: initialActivePath(patterns.entries[0], 'javascript'),
    java: initialActivePath(patterns.entries[0], 'java'),
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
      [language]: buildLangFiles(patterns.entries, language),
    }));
  }, [patterns.entries, language]);

  const activeFolder = activePath.split('/')[0];
  const activeEntry = useMemo(
    () => patterns.entries.find((e) => folderFor(e) === activeFolder) ?? patterns.entries[0],
    [patterns.entries, activeFolder],
  );

  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Patterns`}
      title="Pattern Playbook"
      description="Templates in Python, JavaScript, and Java. Match a trigger, scratch the skeleton in the editor, name the invariant."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section
        title="Pattern templates by language"
        lede="Each entry pairs a problem trigger with the exact state variable to declare and the skeleton code you'd write. Pick your language, find the pattern in the tree, then scratch the template before you start coding logic."
      >
        <LanguageTabs language={language} onChange={setLanguage} />

        <Prose size="sm">
          Read the <strong>Watch</strong> line before you start coding — it flags the single most common mistake for each pattern and saves you from discovering it mid-interview.
        </Prose>

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
            storageKey={`rounds:guide:coding:patterns:${language}`}
          />
        </div>

        <article
          className="card"
          style={{ padding: 'var(--pad-md)', display: 'grid', gap: 'var(--gap-sm)' }}
        >
          <span
            className="mono"
            style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.12em' }}
          >
            {activeEntry.family.toUpperCase()}
          </span>
          <strong style={{ fontSize: 15, fontWeight: 600 }}>{activeEntry.title}</strong>
          <p style={{ margin: 0, color: 'var(--text-3)', fontSize: 12.5, lineHeight: 1.45 }}>
            <strong style={{ color: 'var(--text-2)' }}>When:</strong> {activeEntry.trigger}
          </p>
          <p style={{ margin: 0, color: 'var(--text-3)', fontSize: 12.5, lineHeight: 1.45 }}>
            <strong style={{ color: 'var(--text-2)' }}>State:</strong> {activeEntry.state}
          </p>
          <p style={{ margin: 0, color: 'var(--text-4)', fontSize: 12, lineHeight: 1.45 }}>
            Watch: {activeEntry.watch}
          </p>
        </article>
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
