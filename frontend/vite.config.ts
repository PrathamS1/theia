import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The Theia API runs on :8000. Proxying /api keeps the frontend on
// relative URLs, so no CORS handling and no env var for the host.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
