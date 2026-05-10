import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  ChevronDown,
  ChevronRight,
  ChevronsLeft,
  Code as CodeIcon,
  FileCode,
  FileJson,
  FilePlus2,
  FileText,
  FolderClosed,
  FolderOpen,
  FolderPlus,
} from 'lucide-react';

type Files = Record<string, string>;

type Props = {
  files: Files;
  savedFiles?: Files;
  activePath: string;
  onActivePathChange: (path: string) => void;
  /** Optional virtual folders the user has created but not yet populated.
   *  Tracked so empty-but-expected directories still appear in the tree. */
  virtualFolders?: string[];
  onCreateFile?: (path: string) => void;
  onCreateFolder?: (path: string) => void;
  /** Optional inline collapse button rendered alongside new file/new
   *  folder. Parent owns whether the panel is collapsed. */
  onCollapse?: () => void;
};

// --- iconography ---

function iconFor(path: string) {
  const ext = path.split('.').pop()?.toLowerCase() ?? '';
  if (ext === 'json') return FileJson;
  if (ext === 'md' || ext === 'txt') return FileText;
  if (
    ['ts', 'tsx', 'js', 'jsx', 'py', 'java', 'go', 'rs', 'rb', 'cpp', 'c'].includes(
      ext,
    )
  ) {
    return FileCode;
  }
  return CodeIcon;
}

// --- tree shape ---

type TreeNode =
  | { kind: 'file'; path: string; name: string }
  | { kind: 'dir'; path: string; name: string; children: TreeNode[] };

function buildTree(files: Files, virtualFolders: string[]): TreeNode[] {
  const root: TreeNode = { kind: 'dir', path: '', name: '', children: [] };
  function ensureDir(parts: string[]): TreeNode {
    let cur = root;
    let acc = '';
    for (const p of parts) {
      acc = acc ? `${acc}/${p}` : p;
      const existing = (cur as Extract<TreeNode, { kind: 'dir' }>).children.find(
        (c) => c.kind === 'dir' && c.name === p,
      );
      if (existing && existing.kind === 'dir') {
        cur = existing;
      } else {
        const next: TreeNode = { kind: 'dir', path: acc, name: p, children: [] };
        (cur as Extract<TreeNode, { kind: 'dir' }>).children.push(next);
        cur = next;
      }
    }
    return cur;
  }
  // Files first.
  const paths = Object.keys(files).sort();
  for (const p of paths) {
    const parts = p.split('/');
    const name = parts.pop()!;
    const parent = parts.length
      ? ensureDir(parts)
      : (root as Extract<TreeNode, { kind: 'dir' }>);
    (parent as Extract<TreeNode, { kind: 'dir' }>).children.push({
      kind: 'file',
      path: p,
      name,
    });
  }
  // Virtual folders (empty but tracked).
  for (const f of virtualFolders) {
    if (!f) continue;
    ensureDir(f.split('/'));
  }
  // Sort each level: dirs first (alpha), then files (alpha).
  function sortNode(n: TreeNode) {
    if (n.kind !== 'dir') return;
    n.children.sort((a, b) => {
      if (a.kind !== b.kind) return a.kind === 'dir' ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    n.children.forEach(sortNode);
  }
  sortNode(root);
  return (root as Extract<TreeNode, { kind: 'dir' }>).children;
}

export default function FileExplorer({
  files,
  savedFiles,
  activePath,
  onActivePathChange,
  virtualFolders = [],
  onCreateFile,
  onCreateFolder,
  onCollapse,
}: Props) {
  const tree = useMemo(
    () => buildTree(files, virtualFolders),
    [files, virtualFolders],
  );

  // Expansion state — open every folder by default the first time it
  // appears, so candidates aren't surprised by hidden files.
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  useEffect(() => {
    setExpanded((prev) => {
      const next = new Set(prev);
      // Walk and add any new dir paths.
      const walk = (nodes: TreeNode[]) => {
        for (const n of nodes) {
          if (n.kind === 'dir') {
            if (!prev.has(n.path)) next.add(n.path);
            walk(n.children);
          }
        }
      };
      walk(tree);
      return next;
    });
  }, [tree]);

  // Auto-expand ancestors of the active file so it's always visible.
  useEffect(() => {
    if (!activePath) return;
    const segments = activePath.split('/').slice(0, -1);
    if (!segments.length) return;
    setExpanded((prev) => {
      const next = new Set(prev);
      let acc = '';
      for (const s of segments) {
        acc = acc ? `${acc}/${s}` : s;
        next.add(acc);
      }
      return next;
    });
  }, [activePath]);

  // --- new-file / new-folder inline inputs ---

  const [creating, setCreating] = useState<null | {
    kind: 'file' | 'folder';
    parent: string;
  }>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (creating) inputRef.current?.focus();
  }, [creating]);

  const startCreate = useCallback(
    (kind: 'file' | 'folder', parent: string) => {
      // Make sure parent is expanded so the input is visible.
      if (parent) {
        setExpanded((prev) => {
          if (prev.has(parent)) return prev;
          const next = new Set(prev);
          next.add(parent);
          return next;
        });
      }
      setCreating({ kind, parent });
    },
    [],
  );

  function commitCreate(name: string) {
    const trimmed = name.trim().replace(/^\/+|\/+$/g, '');
    if (!trimmed || !creating) {
      setCreating(null);
      return;
    }
    const fullPath = creating.parent ? `${creating.parent}/${trimmed}` : trimmed;
    if (creating.kind === 'file') {
      onCreateFile?.(fullPath);
      onActivePathChange(fullPath);
    } else {
      onCreateFolder?.(fullPath);
    }
    setCreating(null);
  }

  function isDirty(p: string) {
    return savedFiles ? files[p] !== savedFiles[p] : false;
  }

  function toggleDir(path: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  // --- renderer ---

  function renderNodes(nodes: TreeNode[], depth: number): ReactNode {
    return nodes.map((n) => {
      if (n.kind === 'dir') {
        const open = expanded.has(n.path);
        const FolderIcon = open ? FolderOpen : FolderClosed;
        return (
          <li key={`d:${n.path}`}>
            <button
              type="button"
              onClick={() => toggleDir(n.path)}
              className="w-full text-left flex items-center gap-1.5"
              style={{
                padding: '4px 8px 4px 0',
                paddingLeft: 8 + depth * 12,
                border: 0,
                background: 'transparent',
                color: 'var(--text-3)',
                cursor: 'pointer',
                fontSize: 12,
                lineHeight: 1.3,
                minHeight: 24,
              }}
              aria-expanded={open}
              title={n.path}
            >
              <span style={{ width: 12, display: 'inline-flex' }}>
                {open ? (
                  <ChevronDown size={12} strokeWidth={2} />
                ) : (
                  <ChevronRight size={12} strokeWidth={2} />
                )}
              </span>
              <FolderIcon
                size={13}
                strokeWidth={1.8}
                style={{ flexShrink: 0, opacity: 0.85 }}
              />
              <span
                style={{
                  flex: 1,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {n.name}
              </span>
            </button>
            {open && (
              <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {renderNodes(n.children, depth + 1)}
                {creating?.parent === n.path && (
                  <li>
                    <NewItemInput
                      inputRef={inputRef}
                      kind={creating.kind}
                      depth={depth + 1}
                      onCommit={commitCreate}
                      onCancel={() => setCreating(null)}
                    />
                  </li>
                )}
              </ul>
            )}
          </li>
        );
      }
      const Icon = iconFor(n.path);
      const active = n.path === activePath;
      const dirty = isDirty(n.path);
      return (
        <li key={`f:${n.path}`}>
          <button
            type="button"
            onClick={() => onActivePathChange(n.path)}
            aria-current={active ? 'true' : undefined}
            aria-label={`${n.path}${dirty ? ', unsaved changes' : ''}${active ? ', active file' : ''}`}
            className="w-full text-left flex items-center gap-1.5"
            style={{
              padding: '4px 8px 4px 0',
              paddingLeft: 8 + depth * 12 + 14, // align with sibling-of-folder
              border: 0,
              background: active ? 'var(--accent-soft)' : 'transparent',
              color: active ? 'var(--accent)' : 'var(--text-2)',
              cursor: 'pointer',
              fontSize: 13,
              lineHeight: 1.35,
              minHeight: 28,
            }}
            title={n.path}
          >
            <Icon
              size={13}
              strokeWidth={1.8}
              style={{ flexShrink: 0, opacity: 0.85 }}
            />
            <span
              style={{
                flex: 1,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {n.name}
            </span>
            {dirty && (
              <span
                aria-label="unsaved"
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: 999,
                  background: 'var(--warn)',
                  flexShrink: 0,
                  marginRight: 6,
                }}
              />
            )}
          </button>
        </li>
      );
    });
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div
        className="flex items-center"
        style={{
          padding: '10px 8px 8px 14px',
          gap: 2,
          flexShrink: 0,
        }}
      >
        <span
          className="eyebrow"
          style={{
            color: 'var(--text-3)',
            flex: 1,
            letterSpacing: '0.1em',
            fontSize: 11,
          }}
        >
          Files
        </span>
        {onCreateFile && (
          <button
            type="button"
            onClick={() => startCreate('file', '')}
            aria-label="New file"
            title="New file"
            style={{
              width: 26,
              height: 26,
              border: 0,
              borderRadius: 6,
              background: 'transparent',
              color: 'var(--text-2)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: 'inset 0 0 0 1px var(--border)',
              marginRight: 2,
            }}
          >
            <FilePlus2 size={13} strokeWidth={1.8} />
          </button>
        )}
        {onCreateFolder && (
          <button
            type="button"
            onClick={() => startCreate('folder', '')}
            aria-label="New folder"
            title="New folder"
            style={{
              width: 26,
              height: 26,
              border: 0,
              borderRadius: 6,
              background: 'transparent',
              color: 'var(--text-2)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: 'inset 0 0 0 1px var(--border)',
              marginRight: 2,
            }}
          >
            <FolderPlus size={13} strokeWidth={1.8} />
          </button>
        )}
        {onCollapse && (
          <button
            type="button"
            onClick={onCollapse}
            aria-label="Collapse files panel"
            title="Collapse"
            style={{
              width: 26,
              height: 26,
              border: 0,
              borderRadius: 6,
              background: 'transparent',
              color: 'var(--text-3)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <ChevronsLeft size={14} strokeWidth={2} />
          </button>
        )}
      </div>
      <ul
        style={{
          flex: 1,
          listStyle: 'none',
          margin: 0,
          padding: '0 0 8px',
          overflow: 'auto',
        }}
      >
        {renderNodes(tree, 0)}
        {creating?.parent === '' && (
          <li>
            <NewItemInput
              inputRef={inputRef}
              kind={creating.kind}
              depth={0}
              onCommit={commitCreate}
              onCancel={() => setCreating(null)}
            />
          </li>
        )}
      </ul>
    </div>
  );
}

function NewItemInput({
  kind,
  depth,
  onCommit,
  onCancel,
  inputRef,
}: {
  kind: 'file' | 'folder';
  depth: number;
  onCommit: (name: string) => void;
  onCancel: () => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
}) {
  const [val, setVal] = useState('');
  return (
    <div
      className="flex items-center gap-1.5"
      style={{
        padding: '3px 8px 3px 0',
        paddingLeft: 8 + depth * 12,
        background: 'var(--bg-sunken)',
        minHeight: 26,
      }}
    >
      <span style={{ width: 10 }} />
      {kind === 'folder' ? (
        <FolderClosed
          size={11}
          strokeWidth={1.8}
          style={{ opacity: 0.85, color: 'var(--text-3)' }}
        />
      ) : (
        <FileCode
          size={11}
          strokeWidth={1.8}
          style={{ opacity: 0.85, color: 'var(--text-3)' }}
        />
      )}
      <input
        ref={inputRef as React.RefObject<HTMLInputElement>}
        aria-label={`New ${kind} name`}
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onBlur={() => onCommit(val)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            onCommit(val);
          }
          if (e.key === 'Escape') {
            e.preventDefault();
            onCancel();
          }
        }}
        placeholder={kind === 'folder' ? 'folder-name' : 'name.ext'}
        style={{
          flex: 1,
          background: 'var(--bg)',
          border: 0,
          outline: 'none',
          color: 'var(--text)',
          fontSize: 12,
          padding: '2px 6px',
          borderRadius: 4,
          boxShadow: 'inset 0 0 0 1px var(--border-strong)',
          fontFamily: 'var(--font-sans)',
        }}
      />
    </div>
  );
}
