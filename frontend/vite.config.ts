import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// API target: when running inside docker-compose, the backend service is reachable
// at `http://backend:8000`. When running vite locally on the host (no compose),
// fall back to the host port mapping.
const API_TARGET = process.env.VITE_API_PROXY_TARGET || 'http://backend:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      usePolling: true,
    },
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
});
