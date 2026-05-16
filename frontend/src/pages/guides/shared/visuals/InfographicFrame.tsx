import type { ReactNode } from 'react';

/** Theme-correct wrapper for SVG/CSS infographics. Provides the surrounding
 *  card chrome so individual infographics can focus on their inner artwork. */
export default function InfographicFrame({
  caption,
  children,
  minHeight = 240,
}: {
  caption?: string;
  children: ReactNode;
  minHeight?: number;
}) {
  return (
    <figure
      className="card"
      style={{
        margin: 0,
        padding: 'var(--pad-md)',
        background: 'var(--bg-sunken)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
      }}
    >
      <div
        style={{
          minHeight,
          display: 'grid',
          placeItems: 'center',
          color: 'var(--text-2)',
        }}
      >
        {children}
      </div>
      {caption && (
        <figcaption
          className="mono"
          style={{
            marginTop: 'var(--gap-sm)',
            fontSize: 11,
            color: 'var(--text-4)',
            letterSpacing: '0.1em',
          }}
        >
          {caption.toUpperCase()}
        </figcaption>
      )}
    </figure>
  );
}
