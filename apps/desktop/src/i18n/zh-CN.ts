/**
 * Chinese (Simplified) — default language.
 *
 * v0.4 does NOT translate every existing component string; this
 * file only contains strings for new features added in the v0.4
 * release (ErrorBoundary, update banner, language toggle, etc.).
 * Migrating the existing TopBar / Settings / CommandDock strings
 * is a separate task — tracked in v0.5.
 *
 * The Chinese keys use the original hardcoded strings as values
 * so existing components can swap from literal "中文" → t('...')
 * one at a time without a flag-day.
 */
const zhCN = {
  // ── Language toggle ────────────────────────────────────
  'lang.label': '语言',
  'lang.zh-CN': '中文',
  'lang.en-US': 'English',

  // ── ErrorBoundary ──────────────────────────────────────
  'error.title': '出错了 v{{version}}',
  'error.subtitle': '应用遇到了一个未捕获的错误。下面的信息可以帮助排查问题。',
  'error.message': '错误消息',
  'error.componentStack': '组件堆栈',
  'error.action.copyLogs': '📋 复制日志',
  'error.action.restart': '🔄 重启应用',
  'error.action.report': '🐛 上报问题',
  'error.action.copySuccess': '日志已复制到剪贴板',
  'error.logLocation': '日志同时写入本地文件 {{path}}，可以随附在上报的问题里。',
  'error.copyFallback': '复制以下日志：',
  'error.reportFallback': '复制以下 URL 到浏览器打开：',

  // ── Update banner ──────────────────────────────────────
  'update.available': '⬆ 升级 v{{version}}',
  'update.tooltip': '点击下载并安装最新版本（应用会自动重启）',

  // ── Update install dialog ──────────────────────────────
  'update.confirmTitle': '更新可用',
  'update.confirmBody':
    'Flowntier {{version}} 已就绪可安装，应用将重启。\n\n是否继续？',
  'update.confirmInstall': '安装并重启',
  'update.confirmLater': '稍后',
  'update.failedTitle': '更新失败',
  'update.failedBody':
    '更新安装失败：{{error}}\n\n请从 GitHub Releases 手动下载安装包。',

  // ── Settings (some new bits) ───────────────────────────
  'settings.language': '语言',
};

export type Translations = typeof zhCN;
export default zhCN;