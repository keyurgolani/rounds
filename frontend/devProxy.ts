// The dev server's proxy table (vite.config.ts), kept apart from the
// config so src/__tests__/devProxy.test.ts can check it against
// nginx.conf without loading Vite.
//
// Same routing as the production nginx config so that code written
// against same-origin URLs works in both dev and prod:
//   the paths nginx never proxies           → 404
//   /api/run, /api/evaluate, /api/pdf, /api/share,
//   /api/ai, /api/ai-coding, /api/take-home → runner
//   /api/* (everything else)               → pocketbase
// The admin UI is on PocketBase's own port in dev, as it is in prod.
// Vite tries the entries in order and uses the first that matches, so
// the denials come first; a key starting with ^ is a regular expression
// over the path and query.

import type { ProxyOptions } from 'vite';

// Inside docker compose the sibling services are reachable by name.
// When running vite directly on the host, override via env to point at
// the host ports (e.g. http://127.0.0.1:3099 and http://127.0.0.1:8190).
const RUNNER_TARGET = process.env.VITE_API_PROXY_TARGET || 'http://runner:8000';
const POCKETBASE_TARGET = process.env.VITE_POCKETBASE_PROXY_TARGET || 'http://pocketbase:8090';

// PocketBase's admin UI, the admission hook routes, the admin APIs, and
// collection metadata (nginx.conf, "Never proxied").
const NEVER_PROXIED = [
  '^/_/',
  '^/api/rounds/admission/',
  '^/api/(admins|settings|backups|logs)([/?]|$)',
  '^/api/collections(/[^/?]+)?/?([?]|$)',
];

// A 404 for requests and WebSocket upgrades alike.
function denied(): ProxyOptions {
  return {
    ws: true,
    bypass: () => false,
    configure: (server) => {
      server.ws = (_req, socket) => {
        (socket as { end: (text: string) => void }).end(
          'HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n',
        );
      };
    },
  };
}

export const devProxy: Record<string, ProxyOptions> = {
  ...Object.fromEntries(NEVER_PROXIED.map((path) => [path, denied()])),
  '/api/run': { target: RUNNER_TARGET, changeOrigin: true },
  '/api/evaluate': { target: RUNNER_TARGET, changeOrigin: true },
  '/api/pdf': { target: RUNNER_TARGET, changeOrigin: true },
  '/api/ai-coding': { target: RUNNER_TARGET, changeOrigin: true },
  '/api/sd-practice': { target: RUNNER_TARGET, changeOrigin: true },
  '/api/ai': { target: RUNNER_TARGET, changeOrigin: true },
  '/api/share': { target: RUNNER_TARGET, changeOrigin: true },
  '/api/take-home': { target: RUNNER_TARGET, changeOrigin: true },
  '/api': { target: POCKETBASE_TARGET, changeOrigin: true, ws: true },
};
