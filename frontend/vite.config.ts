import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

import { devProxy } from './devProxy';

const DEV_ALLOWED_HOSTS = (process.env.VITE_DEV_ALLOWED_HOSTS || 'localhost')
  .split(',')
  .map((host) => host.trim())
  .filter(Boolean);

export default defineConfig({
  plugins: [react()],
  // Gates aren't secrets. The dev SPA reads ROUNDS_GATE_* from here the
  // way the nginx image reads them from runtime-config.js.
  envPrefix: ['VITE_', 'ROUNDS_GATE_'],
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      usePolling: true,
    },
    allowedHosts: DEV_ALLOWED_HOSTS,
    // Routing and denials as production nginx has them (devProxy.ts).
    proxy: devProxy,
  },
});
