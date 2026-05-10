import { DiffEditor } from '@monaco-editor/react';
import { useState } from 'react';
import { Check, CheckCircle2, Columns2, Rows3, X } from 'lucide-react';
import { useTheme } from '../../theme/ThemeProvider';

export type PatchProposal = {
  file: string;
  patch_kind: 'replace';
  contents: string;
};

type Props = {
  patches: PatchProposal[];
  /** Files snapshot to diff against. For applied/historical views,
   *  callers pass the pre-apply snapshot so the diff stays visible. */
  currentFiles: Record<string, string>;
  /** Optional — when omitted (or `applied=true`), the action row is
   *  rendered as a read-only "Applied" badge. */
  onApply?: (toApply: PatchProposal[]) => void;
  /** Optional — same behaviour as above. */
  onRejectAll?: () => void;
  /** When true, renders read-only with an "Applied" indicator. */
  applied?: boolean;
};

function languageFromPath(path: string): string {
  if (path.endsWith('.py')) return 'python';
  if (path.endsWith('.ts') || path.endsWith('.tsx')) return 'typescript';
  if (
    path.endsWith('.js') ||
    path.endsWith('.jsx') ||
    path.endsWith('.mjs') ||
    path.endsWith('.cjs')
  )
    return 'javascript';
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

export default function AIPatchView({
  patches,
  currentFiles,
  onApply,
  onRejectAll,
  applied = false,
}: Props) {
  const { theme } = useTheme();
  const [sideBySide, setSideBySide] = useState(false);
  const interactive = !applied && !!onApply;
  return (
    <div
      style={{
        background: 'var(--bg)',
        borderRadius: 'var(--radius)',
        boxShadow: applied
          ? 'inset 0 0 0 1px var(--forest-soft, var(--border))'
          : 'inset 0 0 0 1px var(--border)',
        padding: 6,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      <div
        className="flex items-center"
        style={{ gap: 6, flexWrap: 'wrap' }}
      >
        <span
          className="eyebrow"
          style={{ color: 'var(--text-3)', letterSpacing: '0.1em' }}
        >
          {applied ? 'Applied changes' : 'Proposed changes'} ({patches.length})
        </span>
        <div
          role="tablist"
          aria-label="Diff view"
          className="ml-auto inline-flex"
          style={{
            background: 'var(--bg-sunken)',
            borderRadius: 999,
            boxShadow: 'inset 0 0 0 1px var(--border)',
            padding: 2,
          }}
        >
          <DiffViewBtn
            active={!sideBySide}
            onClick={() => setSideBySide(false)}
            label="Inline"
            icon={<Rows3 size={10} strokeWidth={2} />}
          />
          <DiffViewBtn
            active={sideBySide}
            onClick={() => setSideBySide(true)}
            label="Split"
            icon={<Columns2 size={10} strokeWidth={2} />}
          />
        </div>
        {interactive ? (
          <>
            <button
              type="button"
              onClick={onRejectAll}
              className="inline-flex items-center gap-1"
              style={{
                padding: '4px 10px',
                fontSize: 11,
                fontWeight: 500,
                background: 'transparent',
                color: 'var(--text-2)',
                border: 0,
                borderRadius: 999,
                boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                cursor: 'pointer',
              }}
            >
              <X size={11} strokeWidth={2} />
              Reject all
            </button>
            <button
              type="button"
              onClick={() => onApply!(patches)}
              className="inline-flex items-center gap-1"
              style={{
                padding: '4px 12px',
                fontSize: 11,
                fontWeight: 600,
                background: 'var(--forest)',
                color: 'var(--bg)',
                border: 0,
                borderRadius: 999,
                cursor: 'pointer',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <Check size={11} strokeWidth={2.5} />
              Accept all
            </button>
          </>
        ) : (
          <span
            className="inline-flex items-center gap-1"
            style={{
              padding: '4px 10px',
              fontSize: 11,
              fontWeight: 600,
              background: 'var(--forest-soft, var(--bg-sunken))',
              color: 'var(--forest)',
              borderRadius: 999,
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}
          >
            <CheckCircle2 size={11} strokeWidth={2} />
            Applied
          </span>
        )}
      </div>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 6 }}>
        {patches.map((p) => (
          <li
            key={p.file}
            style={{
              background: 'var(--bg-sunken)',
              borderRadius: 'var(--radius)',
              padding: 6,
            }}
          >
            <div className="flex items-center" style={{ gap: 6, marginBottom: 4 }}>
              <code
                className="mono"
                style={{
                  fontSize: 11.5,
                  color: 'var(--text-2)',
                  padding: '2px 6px',
                  background: 'var(--bg)',
                  borderRadius: 4,
                }}
              >
                {p.file}
              </code>
              {interactive && (
                <button
                  type="button"
                  onClick={() => onApply!([p])}
                  className="inline-flex items-center gap-1"
                  style={{
                    marginLeft: 'auto',
                    padding: '3px 10px',
                    fontSize: 10.5,
                    fontWeight: 600,
                    background: 'var(--forest)',
                    color: 'var(--bg)',
                    border: 0,
                    borderRadius: 999,
                    cursor: 'pointer',
                    letterSpacing: '0.04em',
                  }}
                >
                  <Check size={10} strokeWidth={2.5} />
                  Accept
                </button>
              )}
            </div>
            <div style={{ height: 480, borderRadius: 4, overflow: 'hidden' }}>
              <DiffEditor
                // Force a remount when toggling layout — Monaco's
                // DiffEditor doesn't re-lay out reliably when only
                // `renderSideBySide` changes on an existing instance.
                key={`${p.file}:${sideBySide ? 'split' : 'inline'}`}
                original={currentFiles[p.file] ?? ''}
                modified={p.contents}
                language={languageFromPath(p.file)}
                theme={theme === 'dark' ? 'vs-dark' : 'vs'}
                options={{
                  readOnly: true,
                  renderSideBySide: sideBySide,
                  // CRITICAL: Monaco's DiffEditor silently auto-falls
                  // back to inline view when it deems horizontal space
                  // "limited" — which is true for the ~360px chat
                  // panel we render in. Set this to false so the
                  // user's toggle is always honoured.
                  useInlineViewWhenSpaceIsLimited: false,
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  fontSize: 12,
                  // Show whitespace so users can see indent mismatches.
                  renderWhitespace: 'boundary',
                  // CRITICAL: Monaco defaults this to true, which
                  // silently hides whitespace-only line changes —
                  // exactly the case where the AI re-indented a line
                  // from 8 spaces to 6. Without this flag the diff
                  // looks "identical" but Apply silently breaks
                  // Python indentation. Always show whitespace diffs.
                  ignoreTrimWhitespace: false,
                }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function DiffViewBtn({
  active,
  onClick,
  label,
  icon,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  icon: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      role="tab"
      aria-selected={active}
      className="inline-flex items-center gap-1"
      style={{
        padding: '3px 9px',
        fontSize: 10.5,
        fontWeight: active ? 600 : 500,
        background: active ? 'var(--accent)' : 'transparent',
        color: active ? 'var(--bg)' : 'var(--text-3)',
        border: 0,
        borderRadius: 999,
        cursor: 'pointer',
      }}
    >
      {icon}
      {label}
    </button>
  );
}
