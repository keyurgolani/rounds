import { Link } from 'react-router-dom';
import { mentionLabelWithPrefix, mentionRoute, splitBody } from '../lib/mentions';

// Renders a todo body, turning mention tokens into clickable Links
// while keeping the surrounding plain text intact. Inline-level —
// consumers supply the wrapping element.
export default function MentionText({
  body,
  className,
  style,
}: {
  body: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  const chunks = splitBody(body);
  return (
    <span className={className} style={{ whiteSpace: 'pre-wrap', ...style }}>
      {chunks.map((c, i) => {
        if (c.kind === 'text') return <span key={i}>{c.text}</span>;
        const href = mentionRoute(c.mention);
        return (
          <Link
            key={i}
            to={href}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '0 6px',
              margin: '0 1px',
              borderRadius: 6,
              background: 'var(--accent-soft)',
              color: 'var(--accent)',
              fontSize: 11.5,
              fontWeight: 500,
              textDecoration: 'none',
              lineHeight: '1.5',
            }}
          >
            {mentionLabelWithPrefix(c.mention)}
          </Link>
        );
      })}
    </span>
  );
}
