import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// Tauri-recommended Vite config: fixed port, no HMR over network,
// HMR over WS for the Tauri webview.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    host: '127.0.0.1',
    hmr: {
      protocol: 'ws',
      host: '127.0.0.1',
      port: 1421,
    },
    watch: {
      // Don't watch the Rust side; Tauri handles that.
      ignored: ['**/src-tauri/**'],
    },
  },
  envPrefix: ['VITE_', 'TAURI_'],
  build: {
    target: 'es2022',
    minify: 'esbuild',
    sourcemap: true,
  },
});
