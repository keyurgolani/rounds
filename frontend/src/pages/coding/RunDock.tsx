import React, { useState, useRef, useCallback, ReactNode, useEffect } from 'react';

interface RunDockProps {
  /** Console pane content — usually <ConsoleTab result={...} />. */
  children: ReactNode;
  /** Right-aligned action slot (e.g. last-run timing). */
  rightActions?: ReactNode;
}

const MIN_HEIGHT = 100;
const MAX_HEIGHT = 480;
const DEFAULT_HEIGHT = 180;

// Console-only bottom dock. Cases + Result moved to the right sidebar
// (see RightDock); this strip just holds stdout/stderr below the editor
// and is drag-resizable so users can pull it up when output is long.
export function RunDock({ children, rightActions }: RunDockProps) {
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

  return (
    <div
      data-testid="run-dock"
      style={{
        height,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--paper)',
        borderTop: '1px solid var(--border)',
      }}
    >
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
      <div
        className="flex items-center justify-between"
        style={{
          padding: '6px 12px',
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
        }}
      >
        <span
          className="mono uppercase"
          style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.12em' }}
        >
          Console
        </span>
        <div className="flex items-center gap-2">{rightActions}</div>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 12, minHeight: 0 }}>
        {children}
      </div>
    </div>
  );
}
