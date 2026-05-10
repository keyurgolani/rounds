import React, { useState, useRef, useCallback, ReactNode, useEffect } from 'react';

interface RunDockProps {
  /** Console pane content — usually <ConsoleTab result={...} />. */
  children: ReactNode;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  hasOutput: boolean;
  /** Right-aligned action slot (e.g. last-run timing). */
  rightActions?: ReactNode;
}

const MIN_HEIGHT = 100;
const MAX_HEIGHT = 480;
const DEFAULT_HEIGHT = 180;

// Console-only bottom dock. Cases + Result moved to the right sidebar
// (see RightDock); this strip just holds stdout/stderr below the editor
// and is drag-resizable so users can pull it up when output is long.
//
// When the user hasn't produced any output yet AND the dock is closed,
// the entire strip is hidden — no point in reserving 36px for an empty
// "Console" handle until there's something to show.
export function RunDock({ children, open, onOpenChange, hasOutput, rightActions }: RunDockProps) {
  const [height, setHeight] = useState(DEFAULT_HEIGHT);
  const dragStartY = useRef<number | null>(null);
  const startHeight = useRef(height);

  const onDragStart = useCallback(
    (e: React.MouseEvent) => {
      dragStartY.current = e.clientY;
      startHeight.current = height;
      e.preventDefault();
    },
    [height],
  );

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (dragStartY.current === null) return;
      const delta = dragStartY.current - e.clientY;
      const next = Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, startHeight.current + delta));
      setHeight(next);
    }
    function onUp() {
      dragStartY.current = null;
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  if (!hasOutput && !open) return null;

  return (
    <div
      data-testid="run-dock"
      style={{
        height: open ? height : 36,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--paper)',
        borderTop: '1px solid var(--border)',
        overflow: 'hidden',
        transition: 'height 180ms cubic-bezier(0.22, 0.8, 0.36, 1)',
      }}
    >
      {open && (
        <div
          role="separator"
          aria-orientation="horizontal"
          onMouseDown={onDragStart}
          style={{
            height: 6,
            cursor: 'ns-resize',
            background: 'transparent',
            flexShrink: 0,
          }}
        />
      )}
      <div
        className="flex items-center justify-between"
        style={{
          minHeight: 36,
          padding: '6px 10px 6px 12px',
          borderBottom: open ? '1px solid var(--border)' : 0,
          flexShrink: 0,
        }}
      >
        <button
          type="button"
          onClick={() => onOpenChange(!open)}
          disabled={!hasOutput && !open}
          className="mono uppercase"
          style={{
            fontSize: 9.5,
            color: open ? 'var(--text-3)' : 'var(--text-4)',
            letterSpacing: '0.12em',
            background: 'transparent',
            border: 0,
            padding: 0,
            cursor: hasOutput || open ? 'pointer' : 'default',
          }}
        >
          Console{!open && hasOutput ? ' · output ready' : ''}
        </button>
        <div className="flex items-center gap-2">
          {rightActions}
          {open && (
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              style={{
                border: 0,
                borderRadius: 999,
                background: 'var(--bg-sunken)',
                color: 'var(--text-3)',
                boxShadow: 'inset 0 0 0 1px var(--border)',
                cursor: 'pointer',
                fontSize: 11,
                fontWeight: 500,
                padding: '4px 9px',
              }}
            >
              Collapse
            </button>
          )}
        </div>
      </div>
      {open && (
        <div style={{ flex: 1, overflow: 'auto', padding: 12, minHeight: 0 }}>
          {children}
        </div>
      )}
    </div>
  );
}
