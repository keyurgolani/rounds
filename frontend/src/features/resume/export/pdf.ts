// PDF export. Two paths:
//
//   `exportPdfServer()` — serializes the live preview, posts to
//     /api/pdf/render, downloads the returned blob. Higher fidelity
//     because Puppeteer prints exactly what we send (with our `@page`
//     rules) without browser-specific print-dialog quirks. It goes
//     through `runnerFetch`, so it sends the caller's bearer and one
//     `Idempotency-Key`, and a failure is a `RunnerError` with the
//     status, `code`, and `Retry-After`.
//
//   `exportPdfPrint()` — `window.print()`. Works offline, gives the
//     user the standard system print dialog. Acts as a fallback when
//     the renderer service is down.
//
// Both expect the studio's preview to be in the DOM under
// `[data-resume-page]`.

import { buildStandaloneHtml } from './html';
import { downloadBlob } from './index';
import { runnerFetch } from '../../../lib/runnerFetch';

export async function exportPdfServer(filenameBase: string, marginMm = 0): Promise<void> {
  const html = buildStandaloneHtml();
  if (!html) {
    throw new Error('No resume preview is currently rendered.');
  }
  const res = await runnerFetch('/api/pdf/render', {
    method: 'POST',
    body: { html, margin_mm: marginMm },
    errorPrefix: 'PDF render failed',
  });
  const blob = await res.blob();
  downloadBlob(blob, `${filenameBase}.pdf`);
}

export function exportPdfPrint(): void {
  window.print();
}
