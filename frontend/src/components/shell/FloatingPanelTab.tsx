import type { ReactNode } from 'react';

type Tab = {
  key: string;
  label: string;
  icon?: ReactNode;
  onClick: () => void;
};

type Props = {
  tabs: Tab[];
};

/**
 * Renders a vertical stack of pull-tabs anchored to the left edge of
 * the parent (which must be `position: relative`). Used by the page
 * shell to surface collapsed AI Chat and Files panels at the same
 * anchor without each panel having to know about the others.
 *
 * Tabs are vertically centered as a group so a single tab feels
 * positioned the same way as a stack of two. Each tab is the same
 * 16×96 pull-tab shape we use elsewhere.
 */
export default function FloatingPanelTab({ tabs }: Props) {
  if (tabs.length === 0) return null;
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: '50%',
        transform: 'translateY(-50%)',
        zIndex: 20,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      {tabs.map((t) => (
        <button
          key={t.key}
          type="button"
          onClick={t.onClick}
          aria-label={`Open ${t.label}`}
          title={`Open ${t.label}`}
          style={{
            height: 96,
            width: 16,
            padding: 0,
            border: 0,
            background: 'var(--bg-elev)',
            color: 'var(--text-3)',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            writingMode: 'vertical-rl',
            borderTopRightRadius: 8,
            borderBottomRightRadius: 8,
            boxShadow: 'var(--shadow-card), inset 0 0 0 1px var(--border)',
          }}
        >
          <span
            className="mono"
            style={{
              transform: 'rotate(180deg)',
              fontSize: 9.5,
              letterSpacing: '0.18em',
              color: 'var(--text-3)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            {t.label.toUpperCase()}
          </span>
        </button>
      ))}
    </div>
  );
}
