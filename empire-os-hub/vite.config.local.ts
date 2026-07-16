import path from 'path';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

// Local dev config — no Replit env var requirements, no Replit plugins.
// Original vite.config.ts is kept intact for Replit deployments.

const port = Number(process.env.PORT || '5173');
const basePath = process.env.BASE_PATH || '/';

export default defineConfig({
  base: basePath,
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, 'src'),
      // @assets pointed to ../../attached_assets on Replit — stub it locally
      '@assets': path.resolve(import.meta.dirname, 'src', 'assets'),
    },
    dedupe: ['react', 'react-dom'],
  },
  root: path.resolve(import.meta.dirname),
  build: {
    outDir: path.resolve(import.meta.dirname, 'dist/public'),
    emptyOutDir: true,
  },
  server: {
    port,
    host: '0.0.0.0',
    fs: {
      strict: false,
    },
  },
  preview: {
    port,
    host: '0.0.0.0',
  },
});
