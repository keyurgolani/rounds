import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Inside docker compose the sibling services are reachable by name.
// When running vite directly on the host, override via env to point at
// the host ports (e.g. http://127.0.0.1:3099 and http://127.0.0.1:8190).
const RUNNER_TARGET =
  process.env.VITE_API_PROXY_TARGET || 'http://runner:8000';
const POCKETBASE_TARGET =
  process.env.VITE_POCKETBASE_PROXY_TARGET || 'http://pocketbase:8090';
const DEV_ALLOWED_HOSTS = (process.env.VITE_DEV_ALLOWED_HOSTS || 'localhost')
  .split(',')
  .map((host) => host.trim())
  .filter(Boolean);

// Same routing as the production nginx config so that code written
// against same-origin URLs works in both dev and prod:
//   /api/run, /api/evaluate, /api/execute  → runner
//   /api/* (everything else)               → pocketbase
//   /_/*                                   → pocketbase admin UI
// Vite's proxy picks the longest-matching prefix, so exact-path
// entries win over the `/api` catch-all.
const proxy = {
  '/api/run': { target: RUNNER_TARGET, changeOrigin: true },
  '/api/evaluate': { target: RUNNER_TARGET, changeOrigin: true },
  '/api/execute': { target: RUNNER_TARGET, changeOrigin: true },
  '/api': { target: POCKETBASE_TARGET, changeOrigin: true, ws: true },
  '/_': { target: POCKETBASE_TARGET, changeOrigin: true },
};

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      usePolling: true,
    },
    allowedHosts: DEV_ALLOWED_HOSTS,
    proxy,
  },
});
