// The Legacy Artifact Snapshot materializer (ROUNDS-00A-L04).
//
// An internal service only PocketBase reaches: over Compose's internal
// `materialize` network, and in k8s through k8s/materializer.yaml's
// NetworkPolicy, which admits pods labeled rounds.io/net: pocketbase and
// allows no egress. It holds no secret, writes nothing, and runs non-root
// on a read-only filesystem. PocketBase's legacy snapshot hook
// (pocketbase/pb_hooks/legacy_snapshots.js) and its scan call it, only
// while ROUNDS_GATE_LEGACY_SNAPSHOT_CREATE is on or an operator scans.
//
//   POST /v1/materialize  {template_id, design, data}, application/json
//   GET  /health
//
// /v1/materialize answers 200 with {status: "ok", ...} and the snapshot's
// content, or {status: "ineligible", reason}, and every answer carries
// materializer_digest, the SHA-256 of dist/materialize.mjs. Errors use a
// fixed vocabulary and never echo the request or an error's text:
//   400 invalid_request         not a JSON object of exactly those three keys
//   404 not_found, 405 method_not_allowed
//   413 body_too_large          over MAX_BODY_BYTES; PocketBase reads it as
//                               data_too_large
//   415 unsupported_media_type
//   500 materialize_failed

import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { materialize, SANITIZER_VERSION } from './dist/materialize.mjs';

const BUNDLE = new URL('./dist/materialize.mjs', import.meta.url);
export const MATERIALIZER_DIGEST = `sha256:${createHash('sha256').update(readFileSync(BUNDLE)).digest('hex')}`;
// A resume's design and data are each at most 2 MB in PocketBase, so their
// request fits with room to spare.
export const MAX_BODY_BYTES = 5 * 1024 * 1024;
const PORT = Number(process.env.PORT || 4100);
const FIELDS = ['data', 'design', 'template_id'];

function send(res, status, body) {
  const text = JSON.stringify({ ...body, materializer_digest: MATERIALIZER_DIGEST });
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(text),
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff',
  });
  res.end(text);
}

// The body, or null once it passes MAX_BODY_BYTES (the rest is drained and
// dropped, so the answer still reaches the caller).
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    let over = false;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) over = true;
      if (!over) chunks.push(chunk);
    });
    req.on('end', () => resolve(over ? null : Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

function validRequest(body) {
  if (body === null || typeof body !== 'object' || Array.isArray(body)) return false;
  const keys = Object.keys(body).sort();
  if (keys.length !== FIELDS.length || keys.some((k, i) => k !== FIELDS[i])) return false;
  return body.template_id === null || typeof body.template_id === 'string';
}

async function handle(req, res) {
  const url = req.url ?? '';
  if (url === '/health') {
    if (req.method !== 'GET' && req.method !== 'HEAD') return send(res, 405, { error: 'method_not_allowed' });
    return send(res, 200, { status: 'ok', sanitizer_version: SANITIZER_VERSION });
  }
  if (url !== '/v1/materialize') return send(res, 404, { error: 'not_found' });
  if (req.method !== 'POST') return send(res, 405, { error: 'method_not_allowed' });
  if (!/^application\/json\s*(?:;|$)/i.test(req.headers['content-type'] ?? '')) {
    return send(res, 415, { error: 'unsupported_media_type' });
  }
  if (Number(req.headers['content-length'] ?? 0) > MAX_BODY_BYTES) {
    res.setHeader('connection', 'close');
    send(res, 413, { error: 'body_too_large' });
    req.resume();
    return undefined;
  }
  const raw = await readBody(req);
  if (raw === null) return send(res, 413, { error: 'body_too_large' });
  let body;
  try {
    body = JSON.parse(raw.toString('utf8'));
  } catch {
    return send(res, 400, { error: 'invalid_request' });
  }
  if (!validRequest(body)) return send(res, 400, { error: 'invalid_request' });
  const started = process.hrtime.bigint();
  const result = materialize(body);
  const ms = Number((process.hrtime.bigint() - started) / 1000000n);
  // Content-free: the outcome, its reason, the size, and the time.
  console.log(JSON.stringify({
    event: 'materialize', status: result.status, reason: result.reason ?? null, size_bytes: result.size_bytes ?? null, ms,
  }));
  return send(res, 200, result);
}

export function createServer() {
  const server = http.createServer((req, res) => {
    handle(req, res).catch((err) => {
      console.error('[materializer] request failed:', err?.name || 'Error');
      if (!res.headersSent) send(res, 500, { error: 'materialize_failed' });
      else res.destroy();
    });
  });
  // Only PocketBase calls it, but a stalled request still can't hold a
  // socket open for long.
  server.headersTimeout = 10000;
  server.requestTimeout = 30000;
  server.keepAliveTimeout = 5000;
  return server;
}

// Started as `node server.mjs`; a test imports it without listening.
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const server = createServer();
  server.listen(PORT, '0.0.0.0', () => {
    console.log(JSON.stringify({ event: 'listening', port: PORT, materializer_digest: MATERIALIZER_DIGEST, sanitizer_version: SANITIZER_VERSION }));
  });
  const stop = () => server.close(() => process.exit(0));
  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);
}
