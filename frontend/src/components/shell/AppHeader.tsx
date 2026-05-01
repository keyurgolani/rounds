import { useEffect, useState, type ReactNode } from 'react';
import { Maximize2, Minimize2, Command } from 'lucide-react';
import { useCommandCenter } from '../../command-center/CommandCenterProvider';

const STORAGE_KEY = 'rounds:header-minimal';

type Props = {
  title: string;
  description?: string;
  eyebrow?: ReactNode;
  // Rendered in the expanded (full-mode) header. The 124px row gives
  // these enough breathing room for full-size pill controls, dropdowns,
  // or a compact widget like StreakCard.
  actions?: ReactNode;
  // Rendered in the minimal (44px) header in place of `actions`. Pages
  // that have a chunky `actions` payload should pass a slimmed-down
  // glyph here so focus mode stays a single tight row. Falls back to
  // `actions` when not provided so existing call sites stay valid.
  compactActions?: ReactNode;
};

function readManual(): boolean {
  if (typeof window === 'undefined') return false;
  return window.localStorage.getItem(STORAGE_KEY) === 'true';
}

function useMinimalHeader() {
  const [manual, setManual] = useState<boolean>(readManual);
  const [autoMinimal, setAutoMinimal] = useState<boolean>(() =>
    typeof window !== 'undefined'
      ? window.matchMedia('(max-width: 640px)').matches
      : false,
  );

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 640px)');
    const handler = (e: MediaQueryListEvent) => setAutoMinimal(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const toggleManual = () => {
    const next = !manual;
    setManual(next);
    window.localStorage.setItem(STORAGE_KEY, String(next));
  };

  return { minimal: manual || autoMinimal, manual, toggleManual };
}

export default function AppHeader({
  title,
  description,
  eyebrow,
  actions,
  compactActions,
}: Props) {
  const cc = useCommandCenter();
  const { minimal, manual, toggleManual } = useMinimalHeader();

  // Dev-only nudge: a chunky `actions` payload doesn't compress gracefully
  // into the 44px minimal-mode row. Pages should pass a slim `compactActions`
  // alongside any non-trivial `actions`. The fallback in ActionSlot keeps the
  // page from breaking, but the layout will be ugly. Silent in production.
  if (
    import.meta.env.DEV &&
    minimal &&
    actions !== undefined &&
    compactActions === undefined
  ) {
    // eslint-disable-next-line no-console
    console.warn(
      'AppHeader: `actions` rendered in minimal mode without `compactActions`. ' +
        'Pages with non-trivial actions should provide a slim `compactActions` ' +
        'variant for focus-mode and mobile.',
    );
  }

  return (
    <header
      style={{
        flexShrink: 0,
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg)',
        padding: minimal ? '8px 20px' : '18px 24px 16px',
        height: minimal ? 44 : 124,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
      }}
    >
      {!minimal && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            minHeight: 22,
          }}
        >
          <div
            style={{
              minWidth: 0,
              flex: 1,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontSize: 12,
              color: 'var(--text-3)',
            }}
          >
            {eyebrow}
          </div>
          <ActionSlot
            actions={actions}
            compactActions={compactActions}
            minimal={false}
            manual={manual}
            toggleManual={toggleManual}
            onOpenCC={cc.open}
          />
        </div>
      )}

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          flex: minimal ? 1 : undefined,
        }}
      >
        <h1
          className="display-italic"
          title={typeof title === 'string' ? title : undefined}
          style={{
            margin: 0,
            fontSize: minimal ? 16 : 'clamp(26px, 5vw, 34px)',
            lineHeight: minimal ? 1.1 : 1.05,
            fontWeight: 400,
            minWidth: 0,
            flex: 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {title}
        </h1>
        {minimal && (
          <ActionSlot
            actions={actions}
            compactActions={compactActions}
            minimal={true}
            manual={manual}
            toggleManual={toggleManual}
            onOpenCC={cc.open}
          />
        )}
      </div>

      {!minimal && description && (
        <p
          style={{
            margin: 0,
            color: 'var(--text-3)',
            fontSize: 13.5,
            maxWidth: 720,
            lineHeight: 1.5,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={description}
        >
          {description}
        </p>
      )}
    </header>
  );
}

function ActionSlot({
  actions,
  compactActions,
  minimal,
  manual,
  toggleManual,
  onOpenCC,
}: {
  actions?: ReactNode;
  compactActions?: ReactNode;
  minimal: boolean;
  manual: boolean;
  toggleManual: () => void;
  onOpenCC: () => void;
}) {
  // When we're in minimal mode, prefer the slim `compactActions` slot so
  // pages can swap in a single-glyph control (e.g. StatusAction with
  // compact=true) instead of a full pill. Falls back to `actions` so
  // legacy call sites that don't yet supply a compact variant keep
  // working.
  const slot = minimal ? (compactActions ?? actions) : actions;
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        flexShrink: 0,
      }}
    >
      {slot}
      <button
        type="button"
        onClick={toggleManual}
        aria-label={manual ? 'Expand header' : 'Focus mode (minimize header)'}
        title={manual ? 'Expand header' : 'Focus mode'}
        className="inline-flex items-center justify-center"
        style={{
          width: 28,
          height: 28,
          borderRadius: 6,
          border: 0,
          background: 'transparent',
          color: 'var(--text-3)',
          cursor: 'pointer',
        }}
      >
        {manual ? (
          <Maximize2 size={14} strokeWidth={1.7} />
        ) : (
          <Minimize2 size={14} strokeWidth={1.7} />
        )}
      </button>
      <button
        type="button"
        onClick={onOpenCC}
        aria-label="Open Command Center (⌘K)"
        title="Command Center (⌘K)"
        className="inline-flex items-center gap-1.5"
        style={{
          padding: '5px 10px',
          borderRadius: 6,
          border: '1px solid var(--border)',
          background: 'var(--bg-sunken)',
          color: 'var(--text-2)',
          fontSize: 12,
          cursor: 'pointer',
        }}
      >
        <Command size={12} strokeWidth={1.8} />
        <span className="hidden sm:inline">K</span>
      </button>
    </div>
  );
}
