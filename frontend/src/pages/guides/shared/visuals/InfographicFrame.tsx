import type { ReactNode } from 'react';

/** Theme-correct wrapper for SVG/CSS infographics.
 *
 *  Defaults to shrinking to the child's intrinsic width so narrow
 *  diagrams don't waste horizontal real estate. Pass `wide` to opt into
 *  a full-bleed frame for diagrams that legitimately benefit from the
 *  full column (force/component tables, network maps).
 *
 *  No min-height — frames shrink to content. */
export default function InfographicFrame({
  caption,
  children,
  wide = false,
}: {
  caption?: string;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <figure
      className="card"
      style={{
        margin: 0,
        padding: 'var(--pad-md)',
        background: 'var(--bg-sunken)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
        // Shrink the frame to its content unless the caller opted into a
        // full-width treatment. `max-content` keeps width snug for SVGs
        // with their own maxWidth, while still letting them scale down
        // when the column is narrower.
        width: wide ? '100%' : 'fit-content',
        maxWidth: '100%',
      }}
    >
      <div
        style={{
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
