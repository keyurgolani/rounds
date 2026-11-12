import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

import { devProxy } from './devProxy';

const DEV_ALLOWED_HOSTS = (process.env.VITE_DEV_ALLOWED_HOSTS || 'localhost')
  .split(',')
  .map((host) => host.trim())
  .filter(Boolean);

// The dev and preview servers listen on loopback unless VITE_DEV_HOST
// names another address. The dev container sets it to 0.0.0.0 and
// publishes the port on the host's 127.0.0.1 only (docker-compose.yml).
const DEV_HOST = process.env.VITE_DEV_HOST?.trim() || '127.0.0.1';

export default defineConfig({
  plugins: [react()],
  // Gates aren't secrets. The dev SPA reads ROUNDS_GATE_* from here the
  // way the nginx image reads them from runtime-config.js.
  envPrefix: ['VITE_', 'ROUNDS_GATE_'],
  server: {
    host: DEV_HOST,
    port: 3000,
    watch: {
      usePolling: true,
    },
    allowedHosts: DEV_ALLOWED_HOSTS,
    // Routing and denials as production nginx has them (devProxy.ts).
    proxy: devProxy,
  },
  preview: {
    host: DEV_HOST,
  },
});
