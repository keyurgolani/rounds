import Editor from '@monaco-editor/react';
import { useMemo } from 'react';
import { useTheme } from '../../theme/ThemeProvider';

type Files = Record<string, string>;

type Props = {
  files: Files;
  savedFiles?: Files;
  activePath: string;
  onActivePathChange: (path: string) => void;
  onFileChange: (path: string, contents: string) => void;
  readonlyPaths?: string[];
  height?: number | string;
};

const LANGUAGE_FOR_EXT: Record<string, string> = {
  py: 'python',
  ts: 'typescript',
  tsx: 'typescript',
  js: 'javascript',
  jsx: 'javascript',
  json: 'json',
  md: 'markdown',
};

function languageFor(path: string): string {
  const ext = path.split('.').pop() ?? '';
  return LANGUAGE_FOR_EXT[ext] ?? 'plaintext';
}

/**
 * Multi-file Monaco editor with a left file tree and dirty markers.
 *
 * Fully controlled — parent owns `files`, `activePath`, and notifies of
 * changes via `onFileChange` / `onActivePathChange`. Use `savedFiles` to
 * mark unsaved buffers visually. Monaco's `path` prop preserves per-file
 * cursor position, selection, and undo history across tab switches.
 */
export default function MultiFileEditor({
  files,
  savedFiles,
  activePath,
  onActivePathChange,
  onFileChange,
  readonlyPaths,
  height = '100%',
}: Props) {
  const { theme } = useTheme();
  const paths = useMemo(() => Object.keys(files).sort(), [files]);
  const isDirty = (p: string) => (savedFiles ? files[p] !== savedFiles[p] : false);
  const readonly = readonlyPaths?.includes(activePath) ?? false;

  return (
    <div className="flex" style={{ height }}>
      <aside
        className="border-r"
        style={{ width: 200, background: 'var(--bg-elev)', overflow: 'auto' }}
      >
        <ul className="text-sm">
          {paths.map((p) => (
            <li key={p}>
              <button
                type="button"
                onClick={() => onActivePathChange(p)}
                aria-current={p === activePath ? 'true' : undefined}
                aria-label={`${p}${isDirty(p) ? ', unsaved changes' : ''}${p === activePath ? ', active file' : ''}`}
                className="w-full text-left px-3 py-2 flex items-center gap-2"
                style={{
                  background: p === activePath ? 'var(--accent-soft)' : 'transparent',
                  color: p === activePath ? 'var(--accent)' : 'var(--text-2)',
                }}
              >
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>{p}</span>
                {isDirty(p) && (
                  <span
                    data-testid={`dirty-${p}`}
                    aria-label="unsaved"
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: 999,
                      background: 'var(--warn)',
                    }}
                  />
                )}
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <div className="flex-1">
        <Editor
          height="100%"
          path={activePath}
          language={languageFor(activePath)}
          value={files[activePath] ?? ''}
          theme={theme === 'dark' ? 'vs-dark' : 'vs'}
          onChange={(v) => onFileChange(activePath, v ?? '')}
          options={{ readOnly: readonly, minimap: { enabled: false } }}
        />
      </div>
    </div>
  );
}
