// PDF rendering sidecar.
//
// Accepts an HTML payload and returns a single-file PDF. The HTML is
// loaded via `page.setContent()` (no network round-trip) and external
// requests are blocked by the request interceptor below — both
// hardenings make this safe to expose to the FastAPI proxy without
// auth (the proxy itself enforces session-level rules).
//
// The browser is launched once per process, at startup, and pooled
// across requests to amortize startup cost (~1 s on cold boot, sub-100 ms
// warm). Each render gets its own browser context with one page. Chromium's
// popup blocker stays on (puppeteer turns it off by default), any other
// page that appears in the context is closed at once, and the context
// closes with every page in it when the render ends.
//
// Answers use a fixed vocabulary and never echo the error's text:
//   422 render_timeout  the document didn't load or print in time, which
//                       its content decides; the runner keeps the charge
//   503 unavailable     no browser or page to render with in time
//   500 render_failed   anything else
// The page, load, and print budgets together stay under the runner's 25 s
// wait (backend/routers/pdf.py), so the runner always hears which one it
// was. The render also ends by the load and print budgets' sum, even when
// the document keeps the page from answering at all.

import path from 'node:path';
import { fileURLToPath } from 'node:url';
import express from 'express';
import puppeteer from 'puppeteer-core';

const PORT = Number(process.env.PORT || 4000);
export const PAGE_TIMEOUT_MS = 2000;
export const CONTENT_TIMEOUT_MS = 13000;
export const PDF_TIMEOUT_MS = 8000;
const RENDER_DEADLINE_MS = CONTENT_TIMEOUT_MS + PDF_TIMEOUT_MS;

function timeoutError() {
  const err = new Error('render deadline');
  err.name = 'TimeoutError';
  return err;
}

// `work`, or a TimeoutError once `ms` have passed. Work that ends later
// is ignored.
async function withDeadline(work, ms) {
  work.catch(() => {});
  let timer;
  const deadline = new Promise((_resolve, reject) => {
    timer = setTimeout(() => reject(timeoutError()), ms);
  });
  try {
    return await Promise.race([work, deadline]);
  } finally {
    clearTimeout(timer);
  }
}

// Hold a single browser per process. If it crashes, the next request
// re-launches it.
let browserPromise = null;
export async function getBrowser() {
  if (!browserPromise) {
    browserPromise = puppeteer
      .launch({
        executablePath: '/usr/bin/chromium',
        headless: 'new',
        // Keeps Chromium's popup blocker on, so a document can't open a
        // window.
        ignoreDefaultArgs: ['--disable-popup-blocking'],
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-gpu',
          '--font-render-hinting=none',
          // Every page, the opener and any popup a document still opens,
          // reaches the network only through a closed port, so a request
          // that isn't a data: URL fails to connect instead of leaving
          // the box. The opener's own data: content never needs it (the
          // interceptor serves data: and aborts the rest); this is what
          // contains a popup, which has no interceptor of its own.
          '--proxy-server=127.0.0.1:1',
          '--proxy-bypass-list=<-loopback>',
        ],
      })
      .catch((err) => {
        browserPromise = null;
        throw err;
      });
  }
  return browserPromise;
}

// A new browser context and its one page. Any other page that opens in
// the context is closed at once.
async function openPage() {
  const browser = await getBrowser();
  const context = await browser.createBrowserContext();
  try {
    const page = await context.newPage();
    const own = page.target();
    context.on('targetcreated', (target) => {
      if (target === own || target.type() !== 'page') return;
      target
        .page()
        .then((other) => other?.close())
        .catch(() => {});
    });
    return { context, page };
  } catch (err) {
    context.close().catch(() => {});
    throw err;
  }
}

async function renderPdf(page, html, marginMm) {
  // Disable network access entirely. setContent renders the inline
  // HTML; any <link> / <img> / @font-face URL requests are denied
  // here. This keeps the sidecar from being weaponized as an SSRF
  // probe while still rendering anything self-contained.
  await page.setRequestInterception(true);
  page.on('request', (r) => {
    if (r.url().startsWith('data:')) {
      r.continue();
    } else {
      r.abort();
    }
  });

  await page.setViewport({ width: 794, height: 1123, deviceScaleFactor: 2 });
  await page.setContent(html, { waitUntil: 'load', timeout: CONTENT_TIMEOUT_MS });

  return page.pdf({
    format: 'A4',
    printBackground: true,
    margin: {
      top: `${marginMm}mm`,
      right: `${marginMm}mm`,
      bottom: `${marginMm}mm`,
      left: `${marginMm}mm`,
    },
    preferCSSPageSize: true,
    timeout: PDF_TIMEOUT_MS,
  });
}

export const app = express();
// 5 MB cap on the inbound HTML so an oversized payload can't tie up
// the renderer indefinitely.
app.use(express.json({ limit: '5mb' }));

app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

app.post('/render', async (req, res) => {
  const { html, marginMm = 0 } = req.body ?? {};
  if (typeof html !== 'string' || html.length === 0) {
    res.status(400).json({ error: 'html (string) is required' });
    return;
  }

  // The browser launch and the new page are the sidecar's, not the
  // document's: a stall there is 503, which the runner refunds.
  const opening = openPage();
  let opened;
  try {
    opened = await withDeadline(opening, PAGE_TIMEOUT_MS);
  } catch (err) {
    // A context that opens after the deadline is closed when it does.
    opening.then(({ context }) => context.close()).catch(() => {});
    console.error('[pdf-renderer] no page to render with:', err?.name || 'Error');
    res.status(503).json({ error: 'unavailable' });
    return;
  }
  try {
    const pdf = await withDeadline(renderPdf(opened.page, html, marginMm), RENDER_DEADLINE_MS);
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Cache-Control', 'no-store');
    res.send(Buffer.from(pdf));
  } catch (err) {
    const timedOut = err?.name === 'TimeoutError';
    console.error('[pdf-renderer] render failed:', err?.name || 'Error');
    res.status(timedOut ? 422 : 500).json({ error: timedOut ? 'render_timeout' : 'render_failed' });
  } finally {
    // Every page the render opened goes with its context.
    await opened.context.close().catch(() => {});
  }
});

// Graceful shutdown — close the pooled browser so Chromium doesn't
// leak when the container restarts.
async function shutdown() {
  try {
    const browser = await browserPromise;
    if (browser) await browser.close();
  } catch {
    /* ignore */
  } finally {
    process.exit(0);
  }
}

// Started as `node server.js`; a test imports it without listening.
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[pdf-renderer] listening on :${PORT}`);
  });
  // Launch the browser now, so the first render doesn't wait on it.
  getBrowser().catch((err) => {
    console.error('[pdf-renderer] browser launch failed:', err?.name || 'Error');
  });
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}
