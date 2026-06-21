import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath, URL } from 'node:url';
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

// Tauri-recommended Vite config: fixed port, no HMR over network,
// HMR over WS for the Tauri webview.
//
// `resolve.alias` maps `@tauri-apps/api/*` to no-op stub modules when
// running under Vite (browser mode). The packages/ui hooks check
// `window.__TAURI_INTERNALS__`; under Tauri it's set, under Vite it
// isn't, and the stubs return gracefully.
const STUB_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '.tauri-stubs');
mkdirSync(STUB_DIR, { recursive: true });
const STUB_FILES = {
  'core.js': `export async function invoke() { return null; } export async function convertFileSrc() { return ''; }`,
  'event.js': `export async function listen() { return () => {}; } export async function emit() {}`,
  'shell.js': `export async function open() {} export async function Command() { return { execute: async () => {} }; }`,
  'path.js': `export function appConfigDir() { return ''; } export function resourceDir() { return ''; }`,
};
for (const [name, content] of Object.entries(STUB_FILES)) {
  writeFileSync(resolve(STUB_DIR, name), content, 'utf-8');
}

export default defineConfig(({ command }) => {
  const isDev = command === 'serve';

  return {
    plugins: [react(), tailwindcss()],
    clearScreen: false,
    resolve: {
      // Only stub Tauri APIs in dev mode (browser dev server).
      // In production builds, use real @tauri-apps/api so invoke() works.
      alias: isDev
        ? {
            '@tauri-apps/api/core': fileURLToPath(new URL('./.tauri-stubs/core.js', import.meta.url)),
            '@tauri-apps/api/event': fileURLToPath(new URL('./.tauri-stubs/event.js', import.meta.url)),
            '@tauri-apps/api/shell': fileURLToPath(new URL('./.tauri-stubs/shell.js', import.meta.url)),
            '@tauri-apps/api/path': fileURLToPath(new URL('./.tauri-stubs/path.js', import.meta.url)),
          }
        : {},
    },
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
      ignored: ['**/src-tauri/**', '**/.tauri-stubs/**'],
    },
  },
    envPrefix: ['VITE_', 'TAURI_'],
    build: {
      target: 'es2022',
      minify: 'esbuild',
      sourcemap: true,
    },
  };
});
