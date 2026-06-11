import type { CSSProperties, PointerEvent as ReactPointerEvent, ReactNode, Ref } from 'react';

type Props = {
  children: ReactNode;
  innerRef: Ref<HTMLDivElement>;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  onOpen?: () => void;
  onBeginDrag: (e: ReactPointerEvent<HTMLSpanElement>) => void;
  active: boolean;
  dimmed: boolean;
  isDropTarget: boolean;
  isDragSource: boolean;
  delay?: number;
  side: 'right' | 'left';
  compact?: boolean;
  /** When false, the drag handle is omitted (the card is link-target-only). */
  draggable?: boolean;
  /** Visual flag for board state, e.g. an "unfiled" (no-parent) card. */
  flag?: 'unfiled';
};

export function LinkableCard({
  children,
  innerRef,
  onMouseEnter,
  onMouseLeave,
  onOpen,
  onBeginDrag,
  active,
  dimmed,
  isDropTarget,
  isDragSource,
  delay = 0,
  side,
  compact = false,
  draggable = true,
  flag,
}: Props) {
  const outline = isDropTarget
    ? '0 0 0 2px var(--accent)'
    : active
      ? '0 0 0 1.5px var(--accent)'
      : undefined;

  const style: CSSProperties = {
    position: 'relative',
    padding: compact ? 16 : 20,
    border: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: compact ? 0 : 10,
    animationDelay: `${delay}ms`,
    cursor: onOpen ? 'pointer' : 'default',
    boxShadow: outline,
    outline: flag === 'unfiled' && !active && !isDropTarget ? '1.5px dashed var(--border-strong)' : undefined,
    outlineOffset: 2,
    opacity: dimmed ? 0.42 : 1,
    transform: active ? 'translateY(-1px)' : 'none',
    transition: 'opacity 160ms, transform 160ms, box-shadow 160ms, outline 160ms',
  };

  return (
    <div
      ref={innerRef}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onClick={(e) => {
        if ((e.target as HTMLElement).closest('[data-link-handle]')) return;
        onOpen?.();
      }}
      className="card fade-up"
      style={style}
    >
      {children}

      {draggable && (
      <span
        data-link-handle
        onPointerDown={onBeginDrag}
        title="Drag to link"
        role="button"
        aria-label="Drag to link"
        tabIndex={-1}
        style={{
          position: 'absolute',
          top: '50%',
          [side]: -8,
          transform: 'translateY(-50%)',
          width: 16,
          height: 16,
          borderRadius: 999,
          background: active || isDragSource ? 'var(--accent)' : 'var(--bg-elev)',
          boxShadow:
            active || isDragSource
              ? '0 0 0 2px var(--bg)'
              : '0 0 0 1px var(--border-strong), 0 0 0 3px var(--bg)',
          cursor: 'grab',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 3,
          transition: 'background 140ms, box-shadow 140ms',
          touchAction: 'none',
        }}
      >
        <span
          style={{
            width: 4,
            height: 4,
            borderRadius: 999,
            background: active || isDragSource ? 'var(--bg-elev)' : 'var(--border-strong)',
          }}
        />
      </span>
      )}
    </div>
  );
}
