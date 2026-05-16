import type { CSSProperties, ReactNode } from 'react';

export function Eyebrow({ children }: { children: ReactNode }) {
  return <div className="eyebrow">{children}</div>;
}

export function DisplayHeading({
  level = 2,
  children,
  id,
}: {
  level?: 1 | 2 | 3;
  children: ReactNode;
  id?: string;
}) {
  const Tag = (`h${level}` as 'h1' | 'h2' | 'h3');
  const size = level === 1 ? 'clamp(28px, 4.4vw, 40px)'
             : level === 2 ? 'clamp(22px, 3.4vw, 30px)'
             : 'clamp(18px, 2.4vw, 22px)';
  return (
    <Tag
      id={id}
      className="display-italic"
      style={{
        margin: 0,
        fontSize: size,
        lineHeight: 1.05,
        fontWeight: 400,
        scrollMarginTop: 24,
      }}
    >
      {children}
    </Tag>
  );
}

export function ThesisLine({ children }: { children: ReactNode }) {
  return (
    <p
      className="display-italic"
      style={{
        margin: 0,
        fontSize: 'clamp(22px, 3.2vw, 30px)',
        lineHeight: 1.2,
        color: 'var(--text)',
      }}
    >
      {children}
    </p>
  );
}

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
      <span className="mono" style={{ color: 'var(--text-4)', fontSize: 11, letterSpacing: '0.1em' }}>
        {label.toUpperCase()}
      </span>
      <span style={{ color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.5 }}>{value}</span>
    </div>
  );
}

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
      <strong style={{ display: 'block', fontSize: 15, lineHeight: 1.3, fontWeight: 600 }}>{title}</strong>
      {body && <div style={{ color: 'var(--text-2)', fontSize: 13.5, lineHeight: 1.55 }}>{body}</div>}
      {footer && (
        <div style={{ color: 'var(--text-3)', fontSize: 12.5, lineHeight: 1.45 }}>{footer}</div>
      )}
    </article>
  );
}

export function Section({
  id,
  eyebrow,
  title,
  description,
  children,
}: {
  id?: string;
  eyebrow?: string;
  title?: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="grid" style={{ gap: 'var(--gap-md)', scrollMarginTop: 24 }}>
      {(eyebrow || title || description) && (
        <div className="grid" style={{ gap: 6 }}>
          {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
          {title && <DisplayHeading level={2}>{title}</DisplayHeading>}
          {description && (
            <p style={{ margin: 0, color: 'var(--text-3)', fontSize: 13.5, lineHeight: 1.55, maxWidth: 760 }}>
              {description}
            </p>
          )}
        </div>
      )}
      {children}
    </section>
  );
}

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
      }}
    >
      {children}
    </div>
  );
}

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
