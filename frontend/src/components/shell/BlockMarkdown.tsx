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
  | { kind: 'code'; text: string; lang?: string }
  | { kind: 'hr' };

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
    // Thematic break — three or more hyphens / asterisks / underscores
    // on their own line (with optional spaces). Renders as <hr/>.
    // Matched BEFORE headings so a literal "---" line stays a divider
    // (it would otherwise be ambiguous with a setext-style heading
    // underline, which we don't support).
    if (/^\s*([-*_])\s*(?:\1\s*){2,}$/.test(line)) {
      blocks.push({ kind: 'hr' });
      i += 1;
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
    // Bullet list — gather hyphen/star lines AND their continuation
    // lines (indented or unindented soft-wrapped text that follows an
    // item, until a blank line or a new block).
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length) {
        if (/^\s*[-*]\s+/.test(lines[i])) {
          items.push(lines[i].replace(/^\s*[-*]\s+/, ''));
          i += 1;
          continue;
        }
        if (
          items.length > 0 &&
          lines[i].trim() !== '' &&
          !/^(#{1,3})\s+/.test(lines[i]) &&
          !lines[i].startsWith('```') &&
          !/^\s*\d+\.\s+/.test(lines[i])
        ) {
          // Continuation of the previous item — join with a space so it
          // reflows naturally, matching CommonMark soft-newline behavior.
          items[items.length - 1] += ' ' + lines[i].trim();
          i += 1;
          continue;
        }
        break;
      }
      blocks.push({ kind: 'ul', items });
      continue;
    }
    // Ordered list (same continuation rule as bullet list).
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length) {
        if (/^\s*\d+\.\s+/.test(lines[i])) {
          items.push(lines[i].replace(/^\s*\d+\.\s+/, ''));
          i += 1;
          continue;
        }
        if (
          items.length > 0 &&
          lines[i].trim() !== '' &&
          !/^(#{1,3})\s+/.test(lines[i]) &&
          !lines[i].startsWith('```') &&
          !/^\s*[-*]\s+/.test(lines[i])
        ) {
          items[items.length - 1] += ' ' + lines[i].trim();
          i += 1;
          continue;
        }
        break;
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
      !/^\s*\d+\.\s+/.test(lines[i]) &&
      !/^\s*([-*_])\s*(?:\1\s*){2,}$/.test(lines[i])
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
    // Soft newlines reflow as spaces (CommonMark behavior). A line
    // ending in two trailing spaces opts back into a hard break.
    return (
      <p key={key} style={{ margin: 0 }}>
        {b.lines.map((line, i) => {
          const hardBreak = /  $/.test(line);
          const text = hardBreak ? line.replace(/  +$/, '') : line;
          const last = i === b.lines.length - 1;
          return (
            <span key={i}>
              <InlineMarkdown text={text} as="span" />
              {!last && (hardBreak ? <br /> : ' ')}
            </span>
          );
        })}
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
  if (b.kind === 'hr') {
    // Edge-fading horizontal rule — jkneb/DpJBRN style. A 1px line
    // drawn via a linear gradient that fades to transparent at both
    // ends so the divider sits naturally inside a chat bubble without
    // a hard square cap.
    return (
      <hr
        key={key}
        aria-hidden="true"
        style={{
          margin: '6px 0',
          border: 0,
          height: 1,
          background:
            'linear-gradient(to right, transparent, var(--border-strong), transparent)',
        }}
      />
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
