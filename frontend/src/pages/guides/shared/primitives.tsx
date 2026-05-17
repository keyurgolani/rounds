import type { CSSProperties, ReactNode } from 'react';

/* ---------- Headings ---------------------------------------------------- */

/** Page-level hero heading. Italic display. Use exactly once per page,
 *  inside the page header — not inside content sections. */
export function DisplayHeading({
  level = 1,
  children,
  id,
}: {
  level?: 1 | 2 | 3;
  children: ReactNode;
  id?: string;
}) {
  const Tag = (`h${level}` as 'h1' | 'h2' | 'h3');
  const size =
    level === 1 ? 'clamp(28px, 3.8vw, 36px)'
  : level === 2 ? 'clamp(20px, 2.4vw, 24px)'
  :               'clamp(16px, 1.8vw, 18px)';
  return (
    <Tag
      id={id}
      className="display-italic"
      style={{
        margin: 0,
        fontSize: size,
        lineHeight: 1.1,
        fontWeight: level === 1 ? 500 : 600,
        letterSpacing: level === 1 ? '-0.01em' : 0,
        scrollMarginTop: 24,
      }}
    >
      {children}
    </Tag>
  );
}

/** Small mono caps label. Use sparingly — for chip rows, table column
 *  headers, or as supplementary metadata. NOT as the primary indicator
 *  that "this is a section heading" — Section's title handles that. */
export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div
      className="mono uppercase"
      style={{
        fontSize: 10.5,
        letterSpacing: '0.12em',
        color: 'var(--text-4)',
      }}
    >
      {children}
    </div>
  );
}

/* ---------- Section ----------------------------------------------------- */

/** A study-guide content section. Renders a clearly-visible h2 title and
 *  an optional intro paragraph; children below.
 *
 *  Designed so the heading reads as the section heading (not as another
 *  paragraph of body copy). Use the optional `lede` to give the section
 *  a one-sentence framing line; it lives between the heading and the
 *  body content. */
export function Section({
  id,
  eyebrow,
  title,
  lede,
  children,
}: {
  id?: string;
  eyebrow?: string;
  title?: string;
  lede?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section
      id={id}
      className="grid"
      style={{ gap: 'var(--gap-md)', scrollMarginTop: 24 }}
    >
      {(eyebrow || title || lede) && (
        <header className="grid" style={{ gap: 6 }}>
          {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
          {title && (
            <h2
              style={{
                margin: 0,
                fontSize: 'clamp(20px, 2.4vw, 24px)',
                lineHeight: 1.2,
                fontWeight: 600,
                color: 'var(--text)',
                letterSpacing: '-0.005em',
                scrollMarginTop: 24,
              }}
            >
              {title}
            </h2>
          )}
          {lede && (
            <p
              style={{
                margin: 0,
                color: 'var(--text-3)',
                fontSize: 14.5,
                lineHeight: 1.6,
                maxWidth: '70ch',
              }}
            >
              {lede}
            </p>
          )}
        </header>
      )}
      {children}
    </section>
  );
}

/** A sub-section heading inside a Section. Renders an h3 with a small
 *  accent dot. Use when a Section has 2+ distinct ideas and you want
 *  visual breaks without making them feel like top-level sections. */
export function SubHeading({
  id,
  children,
}: {
  id?: string;
  children: ReactNode;
}) {
  return (
    <h3
      id={id}
      style={{
        margin: 0,
        fontSize: 'clamp(15px, 1.6vw, 17px)',
        lineHeight: 1.3,
        fontWeight: 600,
        color: 'var(--text)',
        scrollMarginTop: 24,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 6,
          height: 6,
          borderRadius: 999,
          background: 'var(--accent)',
          flex: '0 0 auto',
        }}
      />
      {children}
    </h3>
  );
}

/* ---------- Prose ------------------------------------------------------- */

/** Reading-width paragraph block. Use for explanatory text in study
 *  guides — anywhere you would write a short paragraph teaching a
 *  concept. Constrains line length to ~70 characters for legibility. */
export function Prose({
  children,
  size = 'md',
}: {
  children: ReactNode;
  size?: 'sm' | 'md';
}) {
  return (
    <div
      style={{
        color: 'var(--text-2)',
        fontSize: size === 'sm' ? 13.5 : 14.5,
        lineHeight: 1.65,
        maxWidth: '70ch',
      }}
    >
      {children}
    </div>
  );
}

/* ---------- Callout ----------------------------------------------------- */

/** Quoted emphasis — for thesis lines, mantras, or punchy framings.
 *  Renders italic with a left accent bar. Clearly NOT a heading. */
export function Callout({
  children,
  tone = 'accent',
}: {
  children: ReactNode;
  tone?: 'accent' | 'muted';
}) {
  const color =
    tone === 'accent' ? 'var(--accent)' : 'var(--border-strong)';
  return (
    <blockquote
      className="display-italic"
      style={{
        margin: 0,
        padding: '6px 0 6px 16px',
        borderLeft: `3px solid ${color}`,
        fontSize: 'clamp(15px, 1.8vw, 18px)',
        lineHeight: 1.45,
        color: 'var(--text)',
        maxWidth: '60ch',
      }}
    >
      {children}
    </blockquote>
  );
}

/* ---------- Pact / Note panel ------------------------------------------ */

/** Soft-card framed note. Use for "remember this" or "watch out for"
 *  callouts that need a visual container, not just emphasis. */
export function Pact({ children }: { children: ReactNode }) {
  return (
    <div
      className="card"
      style={{
        padding: 'var(--pad-md)',
        background: 'var(--bg-sunken)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
        color: 'var(--text-2)',
        fontSize: 13.5,
        lineHeight: 1.6,
        maxWidth: '70ch',
      }}
    >
      {children}
    </div>
  );
}

/* ---------- Guidance items --------------------------------------------- */

/** A single guidance bullet with a label and explanatory body. Use
 *  this when you would otherwise reach for a one-line chip — chips
 *  read as buzzwords without context; Guidance gives the user the
 *  "what + why". */
export function Guidance({
  label,
  children,
}: {
  label: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="grid" style={{ gap: 4, maxWidth: '70ch' }}>
      <div
        style={{
          fontSize: 14,
          fontWeight: 600,
          color: 'var(--text)',
        }}
      >
        {label}
      </div>
      <div
        style={{
          color: 'var(--text-2)',
          fontSize: 13.5,
          lineHeight: 1.6,
        }}
      >
        {children}
      </div>
    </div>
  );
}

/** Grid of Guidance items. Use as `<GuidanceGrid>` wrapping multiple
 *  `<Guidance>` children — auto-fits 1–3 columns by viewport width. */
export function GuidanceGrid({ children }: { children: ReactNode }) {
  return (
    <div
      className="grid"
      style={{
        gap: 'var(--gap-md)',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
      }}
    >
      {children}
    </div>
  );
}

/* ---------- Key/value ------------------------------------------------- */

export function KeyValueRow({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div
      className="grid"
      style={{
        gridTemplateColumns: '110px minmax(0, 1fr)',
        gap: 'var(--gap-sm)',
        alignItems: 'baseline',
        paddingBlock: 6,
        borderBottom: '1px solid var(--border)',
      }}
    >
      <span
        className="mono"
        style={{ color: 'var(--text-4)', fontSize: 11, letterSpacing: '0.1em' }}
      >
        {label.toUpperCase()}
      </span>
      <span style={{ color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.55 }}>
        {value}
      </span>
    </div>
  );
}

/* ---------- LaneCard --------------------------------------------------- */

export function LaneCard({
  eyebrow,
  title,
  body,
  footer,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  body?: ReactNode;
  footer?: ReactNode;
}) {
  const style: CSSProperties = {
    display: 'grid',
    gap: 'var(--gap-sm)',
    padding: 'var(--pad-md)',
    borderRadius: 'var(--radius)',
    background: 'var(--bg-elev)',
    boxShadow: 'inset 0 0 0 1px var(--border)',
  };
  return (
    <article style={style}>
      {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
      <strong style={{ display: 'block', fontSize: 15, lineHeight: 1.3, fontWeight: 600 }}>
        {title}
      </strong>
      {body && (
        <div style={{ color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.55 }}>
          {body}
        </div>
      )}
      {footer && (
        <div style={{ color: 'var(--text-3)', fontSize: 12.5, lineHeight: 1.45 }}>
          {footer}
        </div>
      )}
    </article>
  );
}

/* ---------- ChipRow ---------------------------------------------------- */

export function ChipRow({ chips }: { chips: string[] }) {
  return (
    <div className="flex flex-wrap" style={{ gap: 'var(--gap-sm)' }}>
      {chips.map((chip) => (
        <span
          key={chip}
          className="pill"
          style={{
            background: 'var(--bg-elev)',
            color: 'var(--text-2)',
            boxShadow: 'inset 0 0 0 1px var(--border)',
            fontSize: 11.5,
          }}
        >
          {chip}
        </span>
      ))}
    </div>
  );
}

/* ---------- Back-compat exports --------------------------------------- */

/** Deprecated alias preserved so existing pages keep compiling while the
 *  redesign rolls out. New code should use `Callout` directly. */
export const ThesisLine = Callout;
