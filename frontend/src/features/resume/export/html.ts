// Standalone HTML export. Captures the live preview's DOM (which already
// has all the inline styles the templates produce) and wraps it in a
// minimal <html> shell. The result is portable: open in any browser,
// print, or attach to an email.
//
// The wrapper carries the same `@page` + `break-inside: avoid` rules
// the live preview uses so the exported file paginates onto A4 pages
// without splitting entries mid-bullet — both when opened in a browser
// and when run through Puppeteer (which uses this exact HTML).

import { RESUME_PAGE_CSS } from '../templates/parts';
import { downloadString } from './index';

export function buildStandaloneHtml(): string | null {
  const node = document.querySelector<HTMLElement>('[data-resume-page]');
  if (!node) return null;
  const inner = node.outerHTML;
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Resume</title>
  <style>
    @page { size: A4; margin: 0; }
    html, body { margin: 0; padding: 0; background: #fff; }
    body { display: flex; justify-content: center; padding: 16px; }
    [data-resume-page] {
      box-shadow: none !important;
      margin: 0 auto;
    }
    @media print {
      body { padding: 0; }
      [data-resume-page] { width: 100% !important; min-height: 100% !important; }
    }
    ${RESUME_PAGE_CSS}
  </style>
</head>
<body>
${inner}
</body>
</html>`;
}

export function exportStandaloneHtml(base: string): boolean {
  const html = buildStandaloneHtml();
  if (!html) return false;
  downloadString(html, `${base}.html`, 'text/html;charset=utf-8');
  return true;
}
