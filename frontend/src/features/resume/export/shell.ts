// The standalone HTML document around one `[data-resume-page]` article.
//
// The client export (`html.ts`) wraps the live preview's article in it,
// and the Legacy Artifact Snapshot materializer (`backend/materializer/`,
// ROUNDS-00A-L04) wraps its server-rendered article in the same function,
// so a snapshot and a browser export share one shell. It stays pure: no DOM,
// no download helpers, and nothing it imports may need a browser, because
// the materializer bundles this file.
//
// The wrapper carries the same `@page` + `break-inside: avoid` rules the
// live preview uses so the exported file paginates onto A4 pages without
// splitting entries mid-bullet, both when opened in a browser and when run
// through Puppeteer (which uses this exact HTML).

import { RESUME_PAGE_CSS } from '../templates/parts';

export function wrapStandaloneHtml(inner: string): string {
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
