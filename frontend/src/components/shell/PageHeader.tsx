import type { ReactNode } from 'react';

type Props = {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  children?: ReactNode;
};

export default function PageHeader({ eyebrow, title, subtitle, children }: Props) {
  return (
    <div
      style={{ borderBottom: '1px solid var(--border)' }}
      className="px-8 pt-7 pb-5 flex items-end justify-between gap-5 flex-wrap"
    >
      <div className="min-w-0">
        {eyebrow && <div className="eyebrow mb-1.5">{eyebrow}</div>}
        <h1
          className="display-italic"
          style={{
            margin: 0,
            fontSize: 38,
            lineHeight: 1.05,
            fontWeight: 400,
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <p
            style={{
              margin: '8px 0 0',
              color: 'var(--text-3)',
              fontSize: 13.5,
              maxWidth: 640,
              lineHeight: 1.55,
            }}
          >
            {subtitle}
          </p>
        )}
      </div>
      {children && <div className="flex gap-2 items-center">{children}</div>}
    </div>
  );
}
