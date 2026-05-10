import Editor from '@monaco-editor/react';
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  Check,
  Copy,
  GripVertical,
  Maximize2,
  MessageSquare,
  Minimize2,
  RotateCcw,
  WrapText,
} from 'lucide-react';
import { useTheme } from '../../theme/ThemeProvider';
import FileExplorer from './FileExplorer';

type Files = Record<string, string>;

type Props = {
  files: Files;
  savedFiles?: Files;
  activePath: string;
  onActivePathChange: (path: string) => void;
  onFileChange: (path: string, contents: string) => void;
  /** Optional virtual folders that the user has created but not yet
   *  populated — passed through to the FileExplorer. */
  virtualFolders?: string[];
  /** Hooks for new file / new folder actions. When provided, the
   *  explorer's header shows the corresponding affordance. */
  onCreateFile?: (path: string) => void;
  onCreateFolder?: (path: string) => void;
  readonlyPaths?: string[];
  height?: number | string;
  /** Optional bottom-right floating action slot (e.g. Run / Submit). */
  bottomActions?: ReactNode;
  /** Whether the surrounding chrome is in "focus mode". When true, the
   *  Focus button shows the exit icon. Independent of the editor —
   *  the parent owns the focus state and decides what to collapse. */
  focused?: boolean;
  /** If supplied, the editor's top-right toolbar gets a Focus button. */
  onFocusToggle?: () => void;
  /** Per-page persistence key for explorer width + collapsed state.
   *  Defaults to a generic key when omitted. */
  storageKey?: string;
  /** When true, the file explorer is not rendered at all — useful for
   *  single-file pages that still want the shared editor chrome. */
  hideExplorer?: boolean;
  /** Parent-owned collapse state for the file explorer. When true the
   *  rail is removed entirely (zero column footprint) so the parent
   *  can render a floating tab elsewhere. */
  explorerCollapsed?: boolean;
  /** Wired into the FileExplorer's inline collapse button. When set,
   *  the button is rendered alongside New File / New Folder. */
  onToggleExplorer?: () => void;
  /** Wired into the FileExplorer's inline Reset button. When set,
   *  the button is rendered (with a confirm prompt) alongside the
   *  other header actions. Parent restores starter files. */
  onResetFiles?: () => void;
  /** Extra elements rendered in the floating top-right toolbar, before
   *  Wrap/Copy/Focus. Used by single-file pages to inject a Language
   *  selector (or similar) into the same toolbar. */
  topRightExtras?: ReactNode;
  /** Optional override for Monaco's `language` prop. When omitted the
   *  language is inferred from the active file's extension. */
  languageOverride?: string;
  /** Optional pass-through of Monaco editor options. Merged on top of
   *  the defaults the component sets. */
  editorOptions?: Record<string, unknown>;
  /** Optional pass-through of Monaco's `onMount` callback. */
  onEditorMount?: Parameters<typeof Editor>[0]['onMount'];
  /** Optional AI chat panel rendered as a right column INSIDE the
   *  editor. When provided, a Sparkles toggle appears in the top-right
   *  floating toolbar; clicking it opens/collapses the rail. The chat
   *  slot is its own resizable + animated column (same UX as the file
   *  explorer on the left). When undefined, no toggle button appears. */
  aiChat?: ReactNode;
  /** Controlled open state for the AI chat rail. Defaults to false. */
  aiChatOpen?: boolean;
  /** Toggle handler. When omitted, the toggle button is rendered as
   *  a no-op (kept here for symmetry with `onFocusToggle`). */
  onToggleAiChat?: () => void;
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

const DEFAULT_EXPLORER_W = 220;
const MIN_EXPLORER_W = 160;
const MAX_EXPLORER_W = 420;
const DEFAULT_CHAT_W = 360;
const MIN_CHAT_W = 260;
// Effectively no cap — let the user drag the chat as wide as they want
// (handy for split diff view). The flex layout means the editor will
// shrink as the chat grows; the user can drag back if it's too tight.
const MAX_CHAT_W = 4000;

/**
 * Multi-file Monaco editor with a directory-tree file explorer on the
 * left (resizable + collapsible) and a floating top-right toolbar
 * (word-wrap + copy + optional focus toggle). Optional `bottomActions`
 * slot floats at the bottom-right of the editor for primary actions
 * like Run / Submit. Fully controlled — parent owns `files`,
 * `activePath`, and notifies of changes via `onFileChange` /
 * `onActivePathChange`.
 */
export default function MultiFileEditor({
  files,
  savedFiles,
  activePath,
  onActivePathChange,
  onFileChange,
  virtualFolders,
  onCreateFile,
  onCreateFolder,
  readonlyPaths,
  height = '100%',
  bottomActions,
  focused,
  onFocusToggle,
  storageKey = 'rounds:editor.explorer',
  hideExplorer = false,
  explorerCollapsed = false,
  onToggleExplorer,
  onResetFiles,
  topRightExtras,
  languageOverride,
  editorOptions,
  onEditorMount,
  aiChat,
  aiChatOpen = false,
  onToggleAiChat,
}: Props) {
  const { theme } = useTheme();
  const readonly = readonlyPaths?.includes(activePath) ?? false;
  const [wordWrap, setWordWrap] = useState<'on' | 'off'>('off');
  const [copied, setCopied] = useState(false);

  // Explorer state — width + collapsed, persisted per-page.
  const widthKey = `${storageKey}.width`;
  const collapsedKey = `${storageKey}.collapsed`;
  const chatWidthKey = `${storageKey}.chatWidth`;
  const [explorerWidth, setExplorerWidth] = useState<number>(() => {
    if (typeof window === 'undefined') return DEFAULT_EXPLORER_W;
    const v = window.localStorage.getItem(widthKey);
    if (!v) return DEFAULT_EXPLORER_W;
    const n = parseInt(v, 10);
    if (Number.isNaN(n)) return DEFAULT_EXPLORER_W;
    return Math.min(MAX_EXPLORER_W, Math.max(MIN_EXPLORER_W, n));
  });
  const [chatWidth, setChatWidth] = useState<number>(() => {
    if (typeof window === 'undefined') return DEFAULT_CHAT_W;
    const v = window.localStorage.getItem(chatWidthKey);
    if (!v) return DEFAULT_CHAT_W;
    const n = parseInt(v, 10);
    if (Number.isNaN(n)) return DEFAULT_CHAT_W;
    return Math.min(MAX_CHAT_W, Math.max(MIN_CHAT_W, n));
  });
  // Width is controlled here; collapsed lives in the parent so the page
  // can render the floating tab alongside others (chat tab) when both
  // panels are closed.
  void collapsedKey;

  // Drag-resize handle (file explorer — left edge).
  const dragStartX = useRef<number | null>(null);
  const startWidth = useRef(explorerWidth);
  const onResizeStart = useCallback(
    (e: React.MouseEvent) => {
      dragStartX.current = e.clientX;
      startWidth.current = explorerWidth;
      e.preventDefault();
    },
    [explorerWidth],
  );
  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (dragStartX.current === null) return;
      const delta = e.clientX - dragStartX.current;
      const next = Math.max(
        MIN_EXPLORER_W,
        Math.min(MAX_EXPLORER_W, startWidth.current + delta),
      );
      setExplorerWidth(next);
    }
    function onUp() {
      if (dragStartX.current !== null) {
        try {
          window.localStorage.setItem(widthKey, String(explorerWidth));
        } catch {
          /* noop */
        }
      }
      dragStartX.current = null;
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [explorerWidth, widthKey]);

  // Drag-resize handle (AI chat rail — right edge of editor area, so
  // dragging LEFT widens the chat).
  const chatDragStartX = useRef<number | null>(null);
  const chatStartWidth = useRef(chatWidth);
  const onChatResizeStart = useCallback(
    (e: React.MouseEvent) => {
      chatDragStartX.current = e.clientX;
      chatStartWidth.current = chatWidth;
      e.preventDefault();
    },
    [chatWidth],
  );
  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (chatDragStartX.current === null) return;
      const delta = chatDragStartX.current - e.clientX; // dragging left widens
      const next = Math.max(
        MIN_CHAT_W,
        Math.min(MAX_CHAT_W, chatStartWidth.current + delta),
      );
      setChatWidth(next);
    }
    function onUp() {
      if (chatDragStartX.current !== null) {
        try {
          window.localStorage.setItem(chatWidthKey, String(chatWidth));
        } catch {
          /* noop */
        }
      }
      chatDragStartX.current = null;
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [chatWidth, chatWidthKey]);

  async function copyActive() {
    const text = files[activePath] ?? '';
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      /* noop */
    }
  }

  return (
    <div className="flex" style={{ height, position: 'relative' }}>
      {/* File explorer (resizable). The column is removed entirely
          when collapsed — parent renders a floating tab elsewhere.
          Hidden entirely in single-file mode (`hideExplorer`). */}
      {!hideExplorer && !explorerCollapsed && (
        <div
          style={{
            width: explorerWidth,
            flexShrink: 0,
            background: 'var(--bg-elev)',
            borderRight: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
            position: 'relative',
            minWidth: 0,
            transition: 'width 160ms cubic-bezier(0.22, 0.8, 0.36, 1)',
          }}
        >
          <FileExplorer
            files={files}
            savedFiles={savedFiles}
            activePath={activePath}
            onActivePathChange={onActivePathChange}
            virtualFolders={virtualFolders}
            onCreateFile={onCreateFile}
            onCreateFolder={onCreateFolder}
            onCollapse={onToggleExplorer}
          />
          {/* Resize handle on the right edge. */}
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize file explorer"
            onMouseDown={onResizeStart}
            style={{
              position: 'absolute',
              top: 0,
              right: -3,
              bottom: 0,
              width: 6,
              cursor: 'col-resize',
              zIndex: 3,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <span
              aria-hidden="true"
              style={{
                opacity: 0,
                color: 'var(--text-4)',
                transition: 'opacity 120ms',
              }}
              className="rounds-resize-grip"
            >
              <GripVertical size={12} strokeWidth={1.8} />
            </span>
            <style>{`
              .rounds-resize-grip { opacity: 0; }
              [role="separator"]:hover .rounds-resize-grip { opacity: 0.6; }
            `}</style>
          </div>
        </div>
      )}

      <div className="flex-1" style={{ position: 'relative', minWidth: 0 }}>
        {/* Floating top-right toolbar — word wrap + copy + optional focus. */}
        <div
          className="hidden sm:flex items-center gap-1"
          style={{
            position: 'absolute',
            top: 8,
            right: 14,
            zIndex: 10,
          }}
        >
          {topRightExtras}
          <button
            type="button"
            onClick={() => setWordWrap((w) => (w === 'on' ? 'off' : 'on'))}
            aria-label={wordWrap === 'on' ? 'Disable word wrap' : 'Enable word wrap'}
            aria-pressed={wordWrap === 'on'}
            title={wordWrap === 'on' ? 'Disable word wrap' : 'Enable word wrap'}
            style={{
              width: 26,
              height: 26,
              border: 0,
              borderRadius: 6,
              background:
                wordWrap === 'on' ? 'var(--accent-soft)' : 'var(--bg-elev)',
              color: wordWrap === 'on' ? 'var(--accent)' : 'var(--text-3)',
              boxShadow: 'inset 0 0 0 1px var(--border-strong)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <WrapText size={12} strokeWidth={1.8} />
          </button>
          <button
            type="button"
            onClick={copyActive}
            aria-label="Copy file contents"
            title={copied ? 'Copied' : 'Copy file'}
            style={{
              width: 26,
              height: 26,
              border: 0,
              borderRadius: 6,
              background: 'var(--bg-elev)',
              color: copied ? 'var(--forest)' : 'var(--text-3)',
              boxShadow: 'inset 0 0 0 1px var(--border-strong)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {copied ? (
              <Check size={12} strokeWidth={2} />
            ) : (
              <Copy size={12} strokeWidth={1.8} />
            )}
          </button>
          {onResetFiles && (
            <button
              type="button"
              onClick={() => {
                const ok = window.confirm(
                  'Reset all files to their original starter contents?\n\nThis will discard every change you have made.',
                );
                if (ok) onResetFiles();
              }}
              aria-label="Reset files to starter"
              title="Reset files to starter"
              style={{
                width: 26,
                height: 26,
                border: 0,
                borderRadius: 6,
                background: 'var(--bg-elev)',
                color: 'var(--text-3)',
                boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <RotateCcw size={12} strokeWidth={1.8} />
            </button>
          )}
          {aiChat && onToggleAiChat && (
            <button
              type="button"
              onClick={onToggleAiChat}
              aria-label={aiChatOpen ? 'Hide AI chat' : 'Open AI chat'}
              aria-pressed={aiChatOpen}
              title={aiChatOpen ? 'Hide AI chat' : 'Open AI chat'}
              style={{
                width: 26,
                height: 26,
                border: 0,
                borderRadius: 6,
                background: aiChatOpen ? 'var(--accent-soft)' : 'var(--bg-elev)',
                color: aiChatOpen ? 'var(--accent)' : 'var(--text-3)',
                boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <MessageSquare size={12} strokeWidth={1.8} />
            </button>
          )}
          {onFocusToggle && (
            <button
              type="button"
              onClick={onFocusToggle}
              aria-label={focused ? 'Exit focus mode' : 'Focus mode (hide panels)'}
              aria-pressed={focused}
              title={focused ? 'Exit focus (Esc)' : 'Focus mode'}
              style={{
                width: 26,
                height: 26,
                border: 0,
                borderRadius: 6,
                background: focused ? 'var(--accent-soft)' : 'var(--bg-elev)',
                color: focused ? 'var(--accent)' : 'var(--text-3)',
                boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {focused ? (
                <Minimize2 size={12} strokeWidth={1.8} />
              ) : (
                <Maximize2 size={12} strokeWidth={1.8} />
              )}
            </button>
          )}
        </div>

        <Editor
          height="100%"
          path={activePath}
          language={languageOverride ?? languageFor(activePath)}
          value={files[activePath] ?? ''}
          theme={theme === 'dark' ? 'vs-dark' : 'vs'}
          onChange={(v) => onFileChange(activePath, v ?? '')}
          onMount={(editor, monaco) => {
            // Built-in Cmd/Ctrl+S: green inset glow flash to confirm
            // the keystroke was handled, and suppress the browser's
            // "save page" dialog. Drafts autosave already; this is
            // visual reassurance only.
            try {
              editor.addCommand(
                monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
                () => {
                  const dom = editor.getDomNode();
                  if (!dom) return;
                  const prev = dom.style.boxShadow;
                  dom.style.boxShadow = 'inset 0 0 0 2px var(--forest)';
                  dom.style.transition = 'box-shadow 140ms';
                  window.setTimeout(() => {
                    dom.style.boxShadow = prev;
                  }, 320);
                },
              );
            } catch {
              /* monaco not ready — silent fallthrough */
            }
            onEditorMount?.(editor, monaco);
          }}
          options={{
            readOnly: readonly,
            minimap: { enabled: false },
            wordWrap,
            scrollBeyondLastLine: false,
            padding: { top: 16, bottom: 60 },
            // Preserve incoming whitespace exactly — important when an
            // AI diff replaces a Python file. Without these, Monaco
            // can re-detect the indentation style from the new content
            // and "normalize" 4-space indents into 2-space (or tabs)
            // which silently breaks Python formatting.
            detectIndentation: false,
            insertSpaces: true,
            tabSize: 4,
            trimAutoWhitespace: false,
            ...(editorOptions ?? {}),
          }}
        />

        {bottomActions && (
          <div
            style={{
              position: 'absolute',
              bottom: 14,
              right: 14,
              zIndex: 10,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            {bottomActions}
          </div>
        )}
      </div>

      {/* AI chat rail (right of the editor). Renders only when the
          parent passed an `aiChat` slot AND the rail is open — when
          collapsed the column is removed entirely (no reserved width)
          so the editor reclaims the full width. The handle on the
          left edge lets the user drag to resize. */}
      {aiChat && aiChatOpen && (
        <div
          style={{
            width: chatWidth,
            flexShrink: 0,
            background: 'var(--bg)',
            borderLeft: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
            position: 'relative',
            minWidth: 0,
            transition: 'width 160ms cubic-bezier(0.22, 0.8, 0.36, 1)',
          }}
        >
          {/* Resize handle on the left edge — drag left to widen. */}
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize AI chat"
            onMouseDown={onChatResizeStart}
            style={{
              position: 'absolute',
              top: 0,
              left: -3,
              bottom: 0,
              width: 6,
              cursor: 'col-resize',
              zIndex: 3,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <span
              aria-hidden="true"
              style={{
                opacity: 0,
                color: 'var(--text-4)',
                transition: 'opacity 120ms',
              }}
              className="rounds-resize-grip"
            >
              <GripVertical size={12} strokeWidth={1.8} />
            </span>
          </div>
          <div style={{ flex: 1, minHeight: 0 }}>{aiChat}</div>
        </div>
      )}
    </div>
  );
}

