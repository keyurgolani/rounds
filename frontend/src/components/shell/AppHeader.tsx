import { useEffect, useState, type CSSProperties, type ReactNode } from 'react';
import { Maximize2, Minimize2, Command } from 'lucide-react';
import { useCommandCenter } from '../../command-center/CommandCenterProvider';
import InlineMarkdown from './InlineMarkdown';
import { usePlatform } from '../../hooks/usePlatform';
import type { PracticeKind } from '../../hooks/progressApi';
import HeaderTimer from './HeaderTimer';

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
  // String for plain titles; ReactNode for inline-edit affordances etc.
  // The browser tooltip (`<el title=…>`) is only set when this is a
  // string to avoid stringifying React children.
  title: string | ReactNode;
  description?: string;
  eyebrow?: ReactNode;
  // Rendered in the expanded (full-mode) header. The expanded row gives
  // these enough breathing room for full-size pill controls, dropdowns,
  // or a compact widget like StreakCard.
  actions?: ReactNode;
  // Rendered in the minimal (44px) header in place of `actions`. Pages
  // that have a chunky `actions` payload should pass a slimmed-down
  // glyph here so focus mode stays a single tight row. Falls back to
  // `chromeActions` when not provided.
  compactActions?: ReactNode;
  // Rendered inline with ChromeButtons (collapse + ⌘K chip) in both
  // expanded and minimal mode. Use this for status toggles, "+ New"
  // buttons, and other compact actions that belong in the chrome area.
  // Only `actions` (e.g. StreakCard) should use the full-height area.
  chromeActions?: ReactNode;
  /**
   * When set, renders a per-question persistent timer in the chrome
   * chip (alongside focus-toggle + ⌘K). Click toggles start/pause,
   * shift-click resets. Persists across sessions/devices via
   * PocketBase.
   */
  timer?: { kind: PracticeKind; id: string | number };
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
  chromeActions,
  timer,
}: Props) {
  const cc = useCommandCenter();
  const { minimal, manual, toggleManual } = useMinimalHeader();

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
          {compactActions ?? chromeActions ?? actions}
          <ChromeButtons
            manual={manual}
            toggleManual={toggleManual}
            onOpenCC={cc.open}
            align="center"
            timer={timer}
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
              // Two lines is enough for the one-line summary
              // of the question prompt without starving the
              // content below of vertical space.
              WebkitLineClamp: 2,
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
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 8,
          flexShrink: 0,
        }}
      >
        {chromeActions}
        <ChromeButtons
          manual={manual}
          toggleManual={toggleManual}
          onOpenCC={cc.open}
          timer={timer}
        />
      </div>
    </header>
  );
}

function ChromeButtons({
  manual,
  toggleManual,
  onOpenCC,
  align,
  timer,
}: {
  manual: boolean;
  toggleManual: () => void;
  onOpenCC: () => void;
  align?: 'start' | 'center';
  timer?: { kind: PracticeKind; id: string | number };
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
        alignSelf: align === 'center' ? 'center' : undefined,
        display: 'inline-flex',
        alignItems: 'center',
        padding: 3,
        borderRadius: 8,
        background: 'var(--bg-sunken)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
        flexShrink: 0,
      }}
    >
      {timer && (
        <>
          <HeaderTimer kind={timer.kind} id={timer.id} />
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
        </>
      )}
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
