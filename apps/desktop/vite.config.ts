import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { execSync } from 'node:child_process';

// Inlined at build time by Vite. Used by ErrorBoundary to render the
// version on the crash screen, and any future in-app "About" / "What's
// new" page. Values come from:
//   __FLOWNTIER_VERSION__   — read from apps/desktop/package.json
//                             (must match tauri.conf.json version).
//   __FLOWNTIER_BUILD_SHA__ — short git SHA, captured at dev/build
//                             start. Empty string in environments
//                             without git (CI before checkout).
function readPackageVersion(): string {
  try {
    // `npm pkg get` is the most portable way across Node versions.
    const out = execSync('npm pkg get version', {
      cwd: __dirname,
      encoding: 'utf-8',
    }).trim();
    // npm pkg get returns the value bare or quoted — strip quotes.
    return out.replace(/^["']|["']$/g, '');
  } catch {
    return '0.0.0-dev';
  }
}

function readGitShortSha(): string {
  try {
    return execSync('git rev-parse --short HEAD', {
      cwd: __dirname,
      encoding: 'utf-8',
    }).trim();
  } catch {
    return '';
  }
}

// Tauri 2 dev mode: the WebView is a real Tauri webview, so the real
// `@tauri-apps/api/*` packages work end-to-end (the IPC bridge is
// injected by Tauri at runtime). Aliasing them to no-op stubs breaks
// invoke() — it would return `null` and the app could not save secrets,
// start workflows, or do anything else.
//
// The previous "stub in dev" hack was a workaround for opening the
// Vite dev URL in a plain browser, where `window.__TAURI_INTERNALS__`
// is missing. We don't ship that workflow: use `pnpm tauri:dev` to
// launch the real WebView, and use `pnpm build && pnpm tauri:build`
// for production installers.
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
  define: {
    // String literals must be quoted exactly — Vite's esbuild
    // replaces the identifier with the value as-is.
    __FLOWNTIER_VERSION__: JSON.stringify(readPackageVersion()),
    __FLOWNTIER_BUILD_SHA__: JSON.stringify(readGitShortSha()),
  },
  build: {
    target: 'es2022',
    minify: 'esbuild',
    sourcemap: true,
  },
});
