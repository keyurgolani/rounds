// PDF rendering sidecar.
//
// Accepts an HTML payload and returns a single-file PDF. The HTML is
// loaded via `page.setContent()` (no network round-trip) and external
// requests are blocked by the request interceptor below — both
// hardenings make this safe to expose to the FastAPI proxy without
// auth (the proxy itself enforces session-level rules).
//
// The browser is launched once per process and pooled across requests
// to amortize startup cost (~1 s on cold boot, sub-100 ms warm).

import express from 'express';
import puppeteer from 'puppeteer-core';

const PORT = Number(process.env.PORT || 4000);

// Hold a single browser per process. If it crashes, the next request
// re-launches it.
let browserPromise = null;
async function getBrowser() {
  if (!browserPromise) {
    browserPromise = puppeteer
      .launch({
        executablePath: '/usr/bin/chromium',
        headless: 'new',
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-gpu',
          '--font-render-hinting=none',
        ],
      })
      .catch((err) => {
        browserPromise = null;
        throw err;
      });
  }
  return browserPromise;
}

const app = express();
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

  let page;
  try {
    const browser = await getBrowser();
    page = await browser.newPage();

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
    await page.setContent(html, { waitUntil: 'load', timeout: 15000 });

    const pdf = await page.pdf({
      format: 'A4',
      printBackground: true,
      margin: {
        top: `${marginMm}mm`,
        right: `${marginMm}mm`,
        bottom: `${marginMm}mm`,
        left: `${marginMm}mm`,
      },
      preferCSSPageSize: true,
    });

    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Cache-Control', 'no-store');
    res.send(Buffer.from(pdf));
  } catch (err) {
    console.error('[pdf-renderer] render failed:', err);
    res.status(500).json({ error: err?.message || 'render failed' });
  } finally {
    if (page) {
      page.close().catch(() => {});
    }
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[pdf-renderer] listening on :${PORT}`);
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
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
