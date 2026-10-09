import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const apiTarget = process.env.LIQUIDTWIN_API_TARGET ?? 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
});
