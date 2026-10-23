import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } } },
  build: { rollupOptions: { output: { manualChunks(id) {
    if (id.includes('/node_modules/d3-')) return 'vendor-d3';
    if (id.includes('/node_modules/recharts/')) return 'vendor-charts';
    if (id.includes('/node_modules/@tanstack/')) return 'vendor-query';
  } } } },
  test: { environment: 'jsdom' },
});
