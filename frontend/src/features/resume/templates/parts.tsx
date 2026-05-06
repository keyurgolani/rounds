// Shared formatters + a couple of layout primitives reused across the
// four built-in templates. Templates own their typography and color
// choices but lean on these helpers so date ranges, dot-separated
// metadata lines, and clickable links read consistently.

import type { ReactNode } from 'react';


// Shared CSS for resume pagination. Mounted once via <ResumePageStyles/>
// inside the live preview, and re-injected verbatim into the HTML
// export wrapper, so what you see on screen is what prints in PDF
// (Puppeteer) and what opens in a browser-printed standalone file.
//
// Two effects:
//   1. Entries (data-page-block) and section headings get
//      `break-inside: avoid` / `break-after: avoid` so the user agent
//      pagination at print time never splits a bullet list across an
//      A4 page boundary mid-entry.
//   2. The screen-only `[data-page-overlay]` strip is hidden during
//      print — the overlay belongs only to the editor, not the export.
export const RESUME_PAGE_CSS = `
  [data-resume-page] [data-page-block] {
    break-inside: avoid;
    page-break-inside: avoid;
  }
  [data-resume-page] section {
    break-inside: avoid-page;
    page-break-inside: auto;
  }
  [data-resume-page] h2 {
    break-after: avoid;
    page-break-after: avoid;
  }
  @media print {
    [data-page-overlay] { display: none !important; }
  }
`;

export function ResumePageStyles() {
  return <style>{RESUME_PAGE_CSS}</style>;
}

export function formatDateRange(start?: string, end?: string, current?: boolean): string {
  const s = start ? formatMonth(start) : '';
  const e = current ? 'Present' : end ? formatMonth(end) : '';
  if (!s && !e) return '';
  if (!s) return e;
  if (!e) return s;
  return `${s} – ${e}`;
}

export function formatMonth(value: string): string {
  // Accept YYYY-MM or YYYY-MM-DD or full ISO; render `MMM YYYY`.
  const m = value.match(/^(\d{4})-(\d{2})/);
  if (!m) return value;
  const [, year, month] = m;
  const monthIdx = Number(month) - 1;
  const monthName = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ][monthIdx];
  return monthName ? `${monthName} ${year}` : value;
}

export function joinNonEmpty(parts: Array<string | undefined>, sep = ' · '): string {
  return parts.filter((p) => Boolean(p && p.trim())).join(sep);
}

// Renders a slim A4 sheet with a configurable margin. The studio
// wraps this in a Zoomable preview; PDF export sets the viewport to
// match the same dimensions so what you see is what you get.
export function A4Page({
  children,
  marginMm = 14,
  background = '#fff',
  color = '#111',
  fontFamily,
  fontSize = 11,
}: {
  children: ReactNode;
  marginMm?: number;
  background?: string;
  color?: string;
  fontFamily?: string;
  fontSize?: number;
}) {
  return (
    <article
      data-resume-page
      style={{
        width: '210mm',
        minHeight: '297mm',
        background,
        color,
        padding: `${marginMm}mm`,
        boxSizing: 'border-box',
        fontFamily: fontFamily ?? "'Inter', system-ui, sans-serif",
        fontSize,
        lineHeight: 1.42,
        boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
        margin: '0 auto',
      }}
    >
      {children}
    </article>
  );
}

export function Hyperlink({ href, children }: { href?: string; children: ReactNode }) {
  if (!href) return <>{children}</>;
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      style={{ color: 'inherit', textDecoration: 'none' }}
    >
      {children}
    </a>
  );
}
