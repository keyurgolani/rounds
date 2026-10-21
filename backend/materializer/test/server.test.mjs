// The materializer's HTTP surface (ROUNDS-00A-L04), in the image like
// materialize.test.mjs. Listens on 127.0.0.1 only.

import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { after, before, describe, it } from 'node:test';

import { createServer, MATERIALIZER_DIGEST, MAX_BODY_BYTES } from '../server.mjs';
import { DESIGN, RICH } from './fixtures.mjs';

let server;
let base;

before(async () => {
  server = createServer();
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(() => new Promise((resolve) => server.close(resolve)));

async function call(path, { method = 'POST', body, type = 'application/json' } = {}) {
  const res = await fetch(`${base}${path}`, {
    method,
    headers: type ? { 'content-type': type } : {},
    body: typeof body === 'string' || body === undefined ? body : JSON.stringify(body),
  });
  const text = await res.text();
  return { status: res.status, headers: res.headers, json: text ? JSON.parse(text) : null };
}

describe('materializer: HTTP', () => {
  it('reports the digest of the bundle it serves', async () => {
    const digest = `sha256:${createHash('sha256').update(readFileSync(new URL('../dist/materialize.mjs', import.meta.url))).digest('hex')}`;
    assert.equal(MATERIALIZER_DIGEST, digest);
    const { status, json, headers } = await call('/health', { method: 'GET', type: null });
    assert.equal(status, 200);
    assert.deepEqual(json, { status: 'ok', sanitizer_version: '1.0.0', materializer_digest: digest });
    assert.equal(headers.get('cache-control'), 'no-store');
  });

  it('answers a snapshot with its digest', async () => {
    const { status, json } = await call('/v1/materialize', { body: { template_id: 'classic', design: DESIGN, data: RICH } });
    assert.equal(status, 200);
    assert.equal(json.status, 'ok');
    assert.equal(json.template_id, 'classic');
    assert.equal(json.materializer_digest, MATERIALIZER_DIGEST);
    assert.match(json.content_checksum, /^sha256:[0-9a-f]{64}$/);
    assert.equal(json.content_checksum, `sha256:${createHash('sha256').update(json.markup, 'utf8').digest('hex')}`);
    assert.deepEqual(Object.keys(json).sort(), [
      'content_checksum', 'data', 'design', 'font_families', 'markup', 'materializer_digest', 'sanitizer_version',
      'size_bytes', 'status', 'template_fallback', 'template_id',
    ]);
  });

  it('answers an ineligible source with its reason and no content', async () => {
    const { status, json } = await call('/v1/materialize', {
      body: { template_id: 'modern', design: { colors: { primary: 'red' } }, data: RICH },
    });
    assert.equal(status, 200);
    assert.deepEqual(json, {
      status: 'ineligible', reason: 'design_out_of_domain', sanitizer_version: '1.0.0', materializer_digest: MATERIALIZER_DIGEST,
    });
  });

  it('refuses anything but the three-field request, and echoes none of it', async () => {
    const bad = [
      ['/v1/materialize', { body: '{"template_id":' }, 400, 'invalid_request'],
      ['/v1/materialize', { body: [] }, 400, 'invalid_request'],
      ['/v1/materialize', { body: { template_id: 'modern', design: {} } }, 400, 'invalid_request'],
      ['/v1/materialize', { body: { template_id: 'modern', design: {}, data: {}, html: '<p>x</p>' } }, 400, 'invalid_request'],
      ['/v1/materialize', { body: { template_id: 7, design: {}, data: {} } }, 400, 'invalid_request'],
      ['/v1/materialize', { body: { template_id: 'modern', design: {}, data: {} }, type: 'text/plain' }, 415, 'unsupported_media_type'],
      ['/v1/materialize', { method: 'GET', type: null }, 405, 'method_not_allowed'],
      ['/health', { body: {} }, 405, 'method_not_allowed'],
      ['/render', { body: { html: '<p>x</p>' } }, 404, 'not_found'],
    ];
    for (const [path, options, wantStatus, error] of bad) {
      const { status, json } = await call(path, options);
      assert.equal(status, wantStatus, `${path} ${JSON.stringify(options).slice(0, 60)}`);
      assert.deepEqual(json, { error, materializer_digest: MATERIALIZER_DIGEST });
    }
  });

  it('answers 413 to a body over the cap', async () => {
    const filler = 'x'.repeat(MAX_BODY_BYTES);
    const { status, json } = await call('/v1/materialize', { body: { template_id: 'modern', design: {}, data: { filler } } });
    assert.equal(status, 413);
    assert.deepEqual(json, { error: 'body_too_large', materializer_digest: MATERIALIZER_DIGEST });
  });
});
