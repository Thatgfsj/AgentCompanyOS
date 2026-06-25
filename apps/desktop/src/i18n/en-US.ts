/**
 * English (United States) — secondary language.
 *
 * v0.4 ships a complete translation only for the strings added
 * with the v0.4 release. The legacy TopBar / Settings / CommandDock
 * text is intentionally not translated yet; the language toggle
 * primarily exists so non-Chinese users can at least see the
 * update banner, error screen, and installer errors in English.
 *
 * When adding new translatable strings, please add them to BOTH
 * this file and zh-CN.ts so the toggle never falls back to the
 * raw key.
 */
import type { Translations } from './zh-CN';

const enUS: Translations = {
  // ── Language toggle ────────────────────────────────────
  'lang.label': 'Language',
  'lang.zh-CN': '中文',
  'lang.en-US': 'English',

  // ── ErrorBoundary ──────────────────────────────────────
  'error.title': 'Something went wrong v{{version}}',
  'error.subtitle':
    'The app hit an uncaught error. The information below can help diagnose the issue.',
  'error.message': 'Error message',
  'error.componentStack': 'Component stack',
  'error.action.copyLogs': '📋 Copy logs',
  'error.action.restart': '🔄 Restart app',
  'error.action.report': '🐛 Report issue',
  'error.action.copySuccess': 'Logs copied to clipboard',
  'error.logLocation':
    'Logs are also written to {{path}} — please attach them in your report.',
  'error.copyFallback': 'Copy the following log:',
  'error.reportFallback': 'Copy this URL to your browser:',

  // ── Update banner ──────────────────────────────────────
  'update.available': '⬆ Upgrade to v{{version}}',
  'update.tooltip': 'Click to download and install (app will restart)',

  // ── Update install dialog ──────────────────────────────
  'update.confirmTitle': 'Update available',
  'update.confirmBody':
    'Flowntier {{version}} is ready to install. The app will restart.\n\nProceed?',
  'update.confirmInstall': 'Install and restart',
  'update.confirmLater': 'Later',
  'update.failedTitle': 'Update failed',
  'update.failedBody':
    'The update failed to install: {{error}}\n\nPlease download manually from GitHub Releases.',

  // ── Settings (some new bits) ───────────────────────────
  'settings.language': 'Language',
};

export default enUS;