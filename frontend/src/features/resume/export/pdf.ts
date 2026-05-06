// PDF export. Two paths:
//
//   `exportPdfServer()` — serializes the live preview, posts to
//     /api/pdf/render, downloads the returned blob. Higher fidelity
//     because Puppeteer prints exactly what we send (with our `@page`
//     rules) without browser-specific print-dialog quirks.
//
//   `exportPdfPrint()` — `window.print()`. Works offline, gives the
//     user the standard system print dialog. Acts as a fallback when
//     the renderer service is down.
//
// Both expect the studio's preview to be in the DOM under
// `[data-resume-page]`.

import { buildStandaloneHtml } from './html';
import { downloadBlob } from './index';

export async function exportPdfServer(filenameBase: string, marginMm = 0): Promise<void> {
  const html = buildStandaloneHtml();
  if (!html) {
    throw new Error('No resume preview is currently rendered.');
  }
  const res = await fetch('/api/pdf/render', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ html, margin_mm: marginMm }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`PDF render failed (${res.status}): ${detail}`);
  }
  const blob = await res.blob();
  downloadBlob(blob, `${filenameBase}.pdf`);
}

export function exportPdfPrint(): void {
  window.print();
}
