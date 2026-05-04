import { useEffect, useState, type CSSProperties, type ReactNode } from 'react';
import { Maximize2, Minimize2, Command } from 'lucide-react';
import { useCommandCenter } from '../../command-center/CommandCenterProvider';
import InlineMarkdown from './InlineMarkdown';
import { usePlatform } from '../../hooks/usePlatform';

// Shared base for the two chrome chip buttons. Each button spreads
// this and adds the properties that differ (size, padding, font).
const CHROME_BTN_BASE: CSSProperties = {
  height: 24,
  border: 0,
  borderRadius: 5,
  background: 'transparent',
  color: 'var(--text-2)',
  cursor: 'pointer',
};

const STORAGE_KEY = 'rounds:header-minimal';

type Props = {
  title: string;
  description?: string;
  eyebrow?: ReactNode;
  // Rendered in the expanded (full-mode) header. The expanded row gives
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

  if (minimal) {
    // Minimal (focus / mobile) mode — single tight row.
    return (
      <header
        style={{
          flexShrink: 0,
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg)',
          padding: '8px 20px',
          height: 44,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <h1
          className="display-italic"
          title={typeof title === 'string' ? title : undefined}
          style={{
            margin: 0,
            fontSize: 16,
            lineHeight: 1.1,
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
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            flexShrink: 0,
          }}
        >
          {compactActions ?? actions}
          <ChromeButtons
            manual={manual}
            toggleManual={toggleManual}
            onOpenCC={cc.open}
            align="center"
          />
        </div>
      </header>
    );
  }

  // Expanded mode — left text column flexes; actions sit in the
  // middle-right; chrome (collapse + ⌘K) is stacked vertically on the
  // far right edge.
  return (
    <header
      style={{
        flexShrink: 0,
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg)',
        padding: '14px 20px',
        minHeight: 124,
        display: 'flex',
        alignItems: 'stretch',
        gap: 14,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: 4,
          minWidth: 0,
          flex: 1,
        }}
      >
        {eyebrow && (
          <div
            style={{
              minWidth: 0,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontSize: 12,
              color: 'var(--text-3)',
            }}
          >
            {eyebrow}
          </div>
        )}
        <h1
          className="display-italic"
          title={typeof title === 'string' ? title : undefined}
          style={{
            margin: 0,
            fontSize: 'clamp(24px, 4.4vw, 32px)',
            lineHeight: 1.1,
            fontWeight: 400,
            minWidth: 0,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {title}
        </h1>
        {description && (
          <div
            title={description}
            style={{
              margin: 0,
              color: 'var(--text-3)',
              fontSize: 13,
              lineHeight: 1.45,
              display: '-webkit-box',
              WebkitBoxOrient: 'vertical',
              // Three lines is enough to surface the salient framing of
              // long problem prompts without starving the editor below
              // of vertical space. Anything longer lives in the body.
              WebkitLineClamp: 3,
              overflow: 'hidden',
            }}
          >
            <InlineMarkdown text={description} as="span" />
          </div>
        )}
      </div>
      {actions && (
        <div
          style={{
            display: 'flex',
            // Center action payloads at their natural height so a
            // 30px-tall pill doesn't get stretched to fill the
            // ~124px expanded header. Widgets that *want* to fill
            // the height (e.g. StreakCard `compact="header"`) opt
            // in via their own `height: '100%'`.
            alignItems: 'center',
            flexShrink: 0,
          }}
        >
          {actions}
        </div>
      )}
      <ChromeButtons
        manual={manual}
        toggleManual={toggleManual}
        onOpenCC={cc.open}
        align="start"
      />
    </header>
  );
}

function ChromeButtons({
  manual,
  toggleManual,
  onOpenCC,
  align,
}: {
  manual: boolean;
  toggleManual: () => void;
  onOpenCC: () => void;
  align: 'start' | 'center';
}) {
  const { modifierSymbol, modifierLabel, isMac } = usePlatform();
  const hint = `Command Center (${modifierLabel}+K)`;

  // Matched-pair chip: both buttons share one outlined container,
  // divided by a hairline. Pinned to the top in expanded mode
  // (`align: 'start'`) so it stays out of the way of vertically-
  // centered actions; centered in the 44px minimal-mode row.
  return (
    <div
      role="toolbar"
      aria-label="Header controls"
      style={{
        alignSelf: align === 'start' ? 'flex-start' : 'center',
        display: 'inline-flex',
        alignItems: 'center',
        padding: 3,
        borderRadius: 8,
        background: 'var(--bg-sunken)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
        flexShrink: 0,
      }}
    >
      <button
        type="button"
        onClick={toggleManual}
        aria-label={manual ? 'Expand header' : 'Focus mode (minimize header)'}
        title={manual ? 'Expand header' : 'Focus mode'}
        className="app-header-chrome-btn inline-flex items-center justify-center"
        style={{
          ...CHROME_BTN_BASE,
          width: 24,
          padding: 0,
        }}
      >
        {manual ? (
          <Maximize2 size={13} strokeWidth={1.7} />
        ) : (
          <Minimize2 size={13} strokeWidth={1.7} />
        )}
      </button>
      <span
        aria-hidden="true"
        style={{
          width: 1,
          height: 14,
          background: 'var(--border-strong)',
          margin: '0 2px',
          flexShrink: 0,
        }}
      />
      <button
        type="button"
        onClick={onOpenCC}
        aria-label={`Open ${hint}`}
        title={hint}
        className="app-header-chrome-btn inline-flex items-center"
        style={{
          ...CHROME_BTN_BASE,
          padding: '0 8px',
          gap: 5,
          fontSize: 11.5,
          whiteSpace: 'nowrap',
        }}
      >
        {/* Command renders heavier than Maximize2/Minimize2, so size 12 reads optically equal to size 13 on the icon-only button. */}
        {isMac ? (
          <Command size={12} strokeWidth={1.8} />
        ) : (
          <span style={{ fontWeight: 500, letterSpacing: 0.2 }}>{modifierSymbol}</span>
        )}
        <span>K</span>
      </button>
    </div>
  );
}
