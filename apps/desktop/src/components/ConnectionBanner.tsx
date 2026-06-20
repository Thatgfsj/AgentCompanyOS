/**
 * ConnectionBanner — shows startup/reconnection status.
 */

import { useConnection } from '../lib/useConnection.js';

export function ConnectionBanner() {
  const { connected, checking, retry } = useConnection(2000);

  if (connected) return null;

  return (
    <div className="flex items-center justify-between bg-status-warn/20 px-4 py-2 text-xs">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-status-warn animate-pulse" />
        <span className="text-status-warn">
          {checking ? '正在连接 runtime...' : '未连接 runtime — Python 端启动中，请稍候'}
        </span>
      </div>
      <button
        type="button"
        onClick={() => void retry()}
        disabled={checking}
        className="rounded bg-surface-1 px-3 py-1 text-xs text-text-secondary hover:text-primary disabled:opacity-50"
      >
        {checking ? '检测中...' : '立即重连'}
      </button>
    </div>
  );
}
