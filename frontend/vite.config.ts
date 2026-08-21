import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// The Theia API runs on :8000. Proxying /api keeps the frontend on
// relative URLs, so no CORS handling and no env var for the host.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // Overridable so the API can be moved off 8000 without editing this file.
        // (A crashed uvicorn can leave an unkillable zombie socket holding 8000 on
        // Windows; pointing at another port is the practical way out.)
        target: process.env.THEIA_API_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
