import { DiffEditor } from '@monaco-editor/react';
import { useTheme } from '../../theme/ThemeProvider';

export type PatchProposal = {
  file: string;
  patch_kind: 'replace';
  contents: string;
};

type Props = {
  patches: PatchProposal[];
  currentFiles: Record<string, string>;
  onApply: (toApply: PatchProposal[]) => void;
  onRejectAll: () => void;
};

function languageFromPath(path: string): string {
  if (path.endsWith('.py')) return 'python';
  if (path.endsWith('.ts') || path.endsWith('.tsx')) return 'typescript';
  if (path.endsWith('.js') || path.endsWith('.jsx') || path.endsWith('.mjs') || path.endsWith('.cjs')) return 'javascript';
  if (path.endsWith('.json')) return 'json';
  if (path.endsWith('.md') || path.endsWith('.markdown')) return 'markdown';
  if (path.endsWith('.css')) return 'css';
  if (path.endsWith('.html') || path.endsWith('.htm')) return 'html';
  if (path.endsWith('.yaml') || path.endsWith('.yml')) return 'yaml';
  if (path.endsWith('.sh') || path.endsWith('.bash')) return 'shell';
  if (path.endsWith('.go')) return 'go';
  if (path.endsWith('.rs')) return 'rust';
  if (path.endsWith('.sql')) return 'sql';
  return 'plaintext';
}

export default function AIPatchView({ patches, currentFiles, onApply, onRejectAll }: Props) {
  const { theme } = useTheme();
  return (
    <div style={{ padding: 8 }}>
      <div className="flex items-center gap-2 mb-2">
        <strong className="text-sm">Proposed changes ({patches.length})</strong>
        <button
          type="button"
          onClick={() => onApply(patches)}
          className="ml-auto px-2 py-1 text-xs"
          style={{ background: 'var(--success)', color: 'var(--bg)', borderRadius: 4 }}
        >
          Accept all
        </button>
        <button
          type="button"
          onClick={onRejectAll}
          className="px-2 py-1 text-xs"
          style={{ background: 'var(--bg-elev-2)', color: 'var(--text-2)', borderRadius: 4 }}
        >
          Reject all
        </button>
      </div>
      <ul className="grid gap-3">
        {patches.map((p) => (
          <li key={p.file} className="card" style={{ padding: 8 }}>
            <div className="flex items-center gap-2 mb-2">
              <code className="text-xs">{p.file}</code>
              <span className="ml-auto flex gap-2">
                <button
                  type="button"
                  onClick={() => onApply([p])}
                  className="px-2 py-0.5 text-xs"
                  style={{ background: 'var(--success)', color: 'var(--bg)', borderRadius: 4 }}
                >
                  Accept
                </button>
              </span>
            </div>
            <div style={{ height: 220 }}>
              <DiffEditor
                original={currentFiles[p.file] ?? ''}
                modified={p.contents}
                language={languageFromPath(p.file)}
                theme={theme === 'dark' ? 'vs-dark' : 'vs'}
                options={{ readOnly: true, renderSideBySide: false, minimap: { enabled: false } }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
