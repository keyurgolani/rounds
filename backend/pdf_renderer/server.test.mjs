// The sidecar against the image's Chromium (ROUNDS-00A-L01). It runs in
// the image, which has Chromium and the packages; CI's pdf-renderer job
// runs it the same way:
//
//   finch build -t rounds-pdf-renderer:test backend/pdf_renderer
//   finch run --rm -v "$PWD/backend/pdf_renderer/server.test.mjs:/app/server.test.mjs:ro" \
//     rounds-pdf-renderer:test node --test server.test.mjs
//
// The image itself ships only server.js.

import assert from 'node:assert/strict';
import http from 'node:http';
import { after, before, test } from 'node:test';

import { app, getBrowser } from './server.js';

let sidecar;
let base;
let listener;
let heard = [];
let elsewhere;

before(async () => {
  listener = http.createServer((req, res) => {
    heard.push(req.url);
    res.end('ok');
  });
  await new Promise((resolve) => listener.listen(0, '127.0.0.1', resolve));
  elsewhere = `http://127.0.0.1:${listener.address().port}`;
  sidecar = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => sidecar.once('listening', resolve));
  base = `http://127.0.0.1:${sidecar.address().port}`;
});

after(async () => {
  sidecar?.close();
  listener?.close();
  const browser = await getBrowser();
  await browser.close();
});

async function render(html) {
  const res = await fetch(`${base}/render`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ html }),
  });
  return { status: res.status, body: Buffer.from(await res.arrayBuffer()) };
}

async function open() {
  const browser = await getBrowser();
  return { contexts: browser.browserContexts().length, pages: (await browser.pages()).length };
}

// What's open once the render's cleanup has run, up to 3 s after it answered.
async function settled(baseline) {
  let now = await open();
  for (let i = 0; i < 30 && (now.contexts !== baseline.contexts || now.pages !== baseline.pages); i += 1) {
    await new Promise((resolve) => setTimeout(resolve, 100));
    now = await open();
  }
  return now;
}

test('a render answers a PDF and leaves no page open', async () => {
  await getBrowser();
  const baseline = await open();
  const { status, body } = await render('<p>hello</p>');
  assert.equal(status, 200);
  assert.equal(body.subarray(0, 5).toString(), '%PDF-');
  assert.deepEqual(await settled(baseline), baseline);
});

test('a document opens no other page and loads nothing but data: URLs', async () => {
  const baseline = await open();
  heard = [];
  const html = `<img src="${elsewhere}/image"><script>window.open('${elsewhere}/window');</script><p>x</p>`;
  const { status } = await render(html);
  assert.equal(status, 200);
  await new Promise((resolve) => setTimeout(resolve, 1500));
  assert.deepEqual(heard, []);
  assert.deepEqual(await settled(baseline), baseline);
});
