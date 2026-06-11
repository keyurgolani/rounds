export type Endpoint = { x: number; y: number };

export type Connector = {
  key: string;
  from: Endpoint;
  to: Endpoint;
  active: boolean;
  dashed?: boolean;
};

type Props = {
  connectors: Connector[];
  drag?: { fromX: number; fromY: number; x: number; y: number } | null;
  hasDropTarget?: boolean;
  /** When true the overlay renders above the card grid (focus-mode edges). */
  onTop?: boolean;
};

export function bezierPath(from: Endpoint, to: Endpoint) {
  const dx = Math.max(40, (to.x - from.x) * 0.5);
  const c1x = from.x + dx;
  const c2x = to.x - dx;
  return `M ${from.x} ${from.y} C ${c1x} ${from.y}, ${c2x} ${to.y}, ${to.x} ${to.y}`;
}

export function ConnectorOverlay({ connectors, drag, hasDropTarget, onTop }: Props) {
  return (
    <svg
      aria-hidden="true"
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: onTop ? 5 : 1,
        overflow: 'visible',
      }}
    >
      <defs>
        <filter id="connector-glow" x="-20%" y="-50%" width="140%" height="200%">
          <feGaussianBlur stdDeviation="2" />
        </filter>
      </defs>
      {connectors.map((c) => {
        const path = bezierPath(c.from, c.to);
        return (
          <g key={c.key}>
            {c.active && (
              <path
                d={path}
                stroke="var(--accent)"
                strokeWidth="4"
                fill="none"
                opacity="0.25"
                filter="url(#connector-glow)"
              />
            )}
            <path
              d={path}
              stroke={c.active ? 'var(--accent)' : 'var(--border-strong)'}
              strokeWidth={c.active ? 1.5 : 1}
              fill="none"
              opacity={c.active ? 1 : 0.5}
              strokeDasharray={c.dashed ? '5 4' : undefined}
              style={{ transition: 'stroke 160ms, opacity 160ms, stroke-width 160ms' }}
            />
            <circle
              cx={c.from.x}
              cy={c.from.y}
              r={c.active ? 3 : 2}
              fill={c.active ? 'var(--accent)' : 'var(--border-strong)'}
              style={{ transition: 'r 160ms, fill 160ms' }}
            />
            <circle
              cx={c.to.x}
              cy={c.to.y}
              r={c.active ? 3 : 2}
              fill={c.active ? 'var(--accent)' : 'var(--border-strong)'}
              style={{ transition: 'r 160ms, fill 160ms' }}
            />
          </g>
        );
      })}
      {drag && (
        <g>
          <path
            d={bezierPath({ x: drag.fromX, y: drag.fromY }, { x: drag.x, y: drag.y })}
            stroke="var(--accent)"
            strokeWidth="1.75"
            fill="none"
            strokeDasharray="4 3"
          />
          <circle cx={drag.fromX} cy={drag.fromY} r="4" fill="var(--accent)" />
          <circle
            cx={drag.x}
            cy={drag.y}
            r={hasDropTarget ? 6 : 4}
            fill={hasDropTarget ? 'var(--accent)' : 'var(--bg-elev)'}
            stroke="var(--accent)"
            strokeWidth="1.5"
          />
        </g>
      )}
    </svg>
  );
}
