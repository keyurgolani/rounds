// Minimal inline markdown renderer.
//
// Handles three constructs: inline code (`foo`), bold (**foo**), and
// italic (*foo*). Good enough for problem statements and constraints;
// we don't need a full markdown parser for snippets that originate
// from our own seed data.

import type { ReactNode } from 'react';

const PATTERN = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;

function renderInline(text: string): ReactNode[] {
  const parts = text.split(PATTERN);
  return parts.map((part, i) => {
    if (!part) return null;
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code
          key={i}
          className="mono"
          style={{
            padding: '1px 6px',
            borderRadius: 4,
            background: 'var(--bg-sunken)',
            boxShadow: 'inset 0 0 0 1px var(--border)',
            fontSize: '0.9em',
            color: 'var(--text)',
          }}
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={i} style={{ fontWeight: 600, color: 'var(--text)' }}>
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith('*') && part.endsWith('*')) {
      return (
        <em
          key={i}
          style={{ fontStyle: 'italic', fontFamily: 'var(--font-display)' }}
        >
          {part.slice(1, -1)}
        </em>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

type Props = {
  text: string;
  as?: 'p' | 'span' | 'div';
  className?: string;
  style?: React.CSSProperties;
};

export default function InlineMarkdown({ text, as = 'span', className, style }: Props) {
  const content = text.split('\n').map((line, i, arr) => (
    <span key={i}>
      {renderInline(line)}
      {i < arr.length - 1 && <br />}
    </span>
  ));

  if (as === 'p') {
    return (
      <p className={className} style={style}>
        {content}
      </p>
    );
  }
  if (as === 'div') {
    return (
      <div className={className} style={style}>
        {content}
      </div>
    );
  }
  return (
    <span className={className} style={style}>
      {content}
    </span>
  );
}
