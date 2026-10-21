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
// Vite tries the entries in order and uses the first that matches. Every
// entry refuses the paths nginx never proxies, so neither the order of
// the entries nor a new one can forward them.

import type { IncomingMessage } from 'node:http';
import type { ProxyOptions } from 'vite';

// Inside docker compose the sibling services are reachable by name.
// When running vite directly on the host, override via env to point at
// the host ports (e.g. http://127.0.0.1:3099 and http://127.0.0.1:8190).
const RUNNER_TARGET = process.env.VITE_API_PROXY_TARGET || 'http://runner:8000';
const POCKETBASE_TARGET = process.env.VITE_POCKETBASE_PROXY_TARGET || 'http://pocketbase:8090';

// PocketBase's admin UI, the admission and execution hook routes, the
// execution service record's routes, the admin APIs, and collection
// metadata (nginx.conf, "Never proxied"). The collection paths match in
// any case, as their nginx locations do (~*).
const NEVER_PROXIED: RegExp[] = [
  /^\/_\//,
  /^\/api\/rounds\/admission\//,
  /^\/api\/rounds\/execution\//,
  /^\/api\/collections\/execution_service\//i,
  /^\/api\/(admins|settings|backups|logs)(\/|$)/,
  /^\/api\/collections(\/[^/]+)?\/?$/i,
];

// Whether nginx refuses this request URL. nginx matches a location
// against the path without its query and with %XX decoded, so this does
// too; a path that doesn't decode is refused.
export function neverProxied(url: string | undefined): boolean {
  let path: string;
  try {
    path = decodeURIComponent((url ?? '').split('?')[0]);
  } catch {
    return true;
  }
  return NEVER_PROXIED.some((pattern) => pattern.test(path));
}

type Socket = { end: (text: string) => void };

function refuseUpgrade(socket: Socket): void {
  socket.end('HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n');
}

// A 404 for requests and WebSocket upgrades alike.
function denied(): ProxyOptions {
  return {
    ws: true,
    bypass: () => false,
    configure: (server) => {
      server.ws = (_req, socket) => refuseUpgrade(socket as Socket);
    },
  };
}

// `options`, refusing the paths nginx never proxies: a request gets
// Vite's 404, and an upgrade, when the entry carries them, a 404 too.
function guarded(options: ProxyOptions): ProxyOptions {
  return {
    ...options,
    bypass: (req: IncomingMessage) => (neverProxied(req.url) ? false : undefined),
    configure: options.ws
      ? (server) => {
          const forward = server.ws.bind(server);
          server.ws = (req, socket, head, ...rest) =>
            neverProxied(req.url) ? refuseUpgrade(socket as Socket) : forward(req, socket, head, ...rest);
        }
      : undefined,
  };
}

export const devProxy: Record<string, ProxyOptions> = {
  '^/_/': denied(),
  '/api/run': guarded({ target: RUNNER_TARGET, changeOrigin: true }),
  '/api/evaluate': guarded({ target: RUNNER_TARGET, changeOrigin: true }),
  '/api/pdf': guarded({ target: RUNNER_TARGET, changeOrigin: true }),
  '/api/ai-coding': guarded({ target: RUNNER_TARGET, changeOrigin: true }),
  '/api/sd-practice': guarded({ target: RUNNER_TARGET, changeOrigin: true }),
  '/api/ai': guarded({ target: RUNNER_TARGET, changeOrigin: true }),
  '/api/share': guarded({ target: RUNNER_TARGET, changeOrigin: true }),
  '/api/take-home': guarded({ target: RUNNER_TARGET, changeOrigin: true }),
  '/api': guarded({ target: POCKETBASE_TARGET, changeOrigin: true, ws: true }),
};
