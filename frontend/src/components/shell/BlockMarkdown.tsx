// Block-aware markdown renderer for problem descriptions.
//
// Handles paragraphs, bullet/ordered lists, ATX headings (# .. ###),
// fenced code blocks, plus the inline constructs (bold, italic,
// inline code) inherited from InlineMarkdown. We don't reach for a
// real markdown library because (a) descriptions are authored in
// our own seed and use a known subset, (b) we want zero new
// dependencies, and (c) this stays under 150 lines.

import type { ReactNode } from 'react';
import InlineMarkdown from './InlineMarkdown';

type Props = {
  text: string;
  className?: string;
  style?: React.CSSProperties;
};

type Block =
  | { kind: 'p'; lines: string[] }
  | { kind: 'ul'; items: string[] }
  | { kind: 'ol'; items: string[] }
  | { kind: 'h'; level: 1 | 2 | 3; text: string }
  | { kind: 'code'; text: string; lang?: string };

function parse(source: string): Block[] {
  const lines = source.split('\n');
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    // Fenced code block.
    if (line.startsWith('```')) {
      const lang = line.slice(3).trim() || undefined;
      const buf: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].startsWith('```')) {
        buf.push(lines[i]);
        i += 1;
      }
      i += 1; // skip closing fence (or end)
      blocks.push({ kind: 'code', text: buf.join('\n'), lang });
      continue;
    }
    // ATX heading.
    const heading = /^(#{1,3})\s+(.+)$/.exec(line);
    if (heading) {
      blocks.push({
        kind: 'h',
        level: heading[1].length as 1 | 2 | 3,
        text: heading[2].trim(),
      });
      i += 1;
      continue;
    }
    // Bullet list.
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ''));
        i += 1;
      }
      blocks.push({ kind: 'ul', items });
      continue;
    }
    // Ordered list.
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ''));
        i += 1;
      }
      blocks.push({ kind: 'ol', items });
      continue;
    }
    // Blank line — paragraph break.
    if (line.trim() === '') {
      i += 1;
      continue;
    }
    // Paragraph: gather contiguous non-blank, non-special lines.
    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].startsWith('```') &&
      !/^(#{1,3})\s+/.test(lines[i]) &&
      !/^\s*[-*]\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i])
    ) {
      para.push(lines[i]);
      i += 1;
    }
    if (para.length) blocks.push({ kind: 'p', lines: para });
  }
  return blocks;
}

function renderBlock(b: Block, key: number): ReactNode {
  if (b.kind === 'p') {
    return (
      <p key={key} style={{ margin: 0 }}>
        {b.lines.map((line, i) => (
          <span key={i}>
            <InlineMarkdown text={line} as="span" />
            {i < b.lines.length - 1 && <br />}
          </span>
        ))}
      </p>
    );
  }
  if (b.kind === 'ul') {
    return (
      <ul
        key={key}
        style={{
          margin: 0,
          paddingLeft: 18,
          listStyleType: 'disc',
        }}
      >
        {b.items.map((it, i) => (
          <li key={i} style={{ marginBottom: 2 }}>
            <InlineMarkdown text={it} as="span" />
          </li>
        ))}
      </ul>
    );
  }
  if (b.kind === 'ol') {
    return (
      <ol
        key={key}
        style={{
          margin: 0,
          paddingLeft: 22,
          listStyleType: 'decimal',
        }}
      >
        {b.items.map((it, i) => (
          <li key={i} style={{ marginBottom: 2 }}>
            <InlineMarkdown text={it} as="span" />
          </li>
        ))}
      </ol>
    );
  }
  if (b.kind === 'h') {
    const fontSize = b.level === 1 ? 18 : b.level === 2 ? 16 : 14;
    return (
      <div
        key={key}
        style={{
          fontSize,
          fontWeight: 600,
          color: 'var(--text)',
          margin: '4px 0 2px',
        }}
      >
        <InlineMarkdown text={b.text} as="span" />
      </div>
    );
  }
  // Code block — multi-line monospace, sunken background.
  return (
    <pre
      key={key}
      className="mono"
      style={{
        margin: 0,
        padding: '10px 12px',
        borderRadius: 6,
        background: 'var(--bg-sunken)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
        fontSize: '0.9em',
        color: 'var(--text)',
        overflowX: 'auto',
        whiteSpace: 'pre',
      }}
    >
      {b.text}
    </pre>
  );
}

export default function BlockMarkdown({ text, className, style }: Props) {
  const blocks = parse(text);
  return (
    <div
      className={className}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        ...style,
      }}
    >
      {blocks.map((b, i) => renderBlock(b, i))}
    </div>
  );
}
