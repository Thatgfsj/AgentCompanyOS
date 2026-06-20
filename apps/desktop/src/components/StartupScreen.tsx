/**
 * StartupScreen — shown while waiting for the runtime to start.
 */

import { useEffect, useState } from 'react';
import { ensureConnected } from '../lib/api.js';

interface StartupScreenProps {
  onReady: () => void;
}

export function StartupScreen({ onReady }: StartupScreenProps) {
  const [status, setStatus] = useState<'connecting' | 'retrying' | 'failed'>('connecting');
  const [attempts, setAttempts] = useState(0);
  const MAX_ATTEMPTS = 30; // 60 seconds

  useEffect(() => {
    let cancelled = false;

    const connect = async () => {
      for (let i = 1; i <= MAX_ATTEMPTS; i++) {
        if (cancelled) return;
        setAttempts(i);

        const ok = await ensureConnected(0); // single check, no internal retry
        if (ok) {
          if (!cancelled) onReady();
          return;
        }

        setStatus(i > 5 ? 'retrying' : 'connecting');
        await new Promise(r => setTimeout(r, 2000));
      }

      if (!cancelled) setStatus('failed');
    };

    void connect();
    return () => { cancelled = true; };
  }, [onReady]);

  return (
    <div className="flex h-screen items-center justify-center bg-surface-1">
      <div className="flex flex-col items-center gap-6">
        {/* Logo */}
        <div className="text-4xl font-bold text-primary">Agent Company OS</div>
        <div className="text-sm text-text-secondary">AI 软件公司操作系统</div>

        {/* Spinner */}
        <div className="mt-4 flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-chief" />

          {status === 'connecting' && (
            <div className="text-sm text-text-secondary">
              正在启动 Python 运行时... ({attempts}/{MAX_ATTEMPTS})
            </div>
          )}

          {status === 'retrying' && (
            <div className="text-sm text-status-warn">
              启动较慢，请稍候... ({attempts}/{MAX_ATTEMPTS})
            </div>
          )}

          {status === 'failed' && (
            <div className="flex flex-col items-center gap-3">
              <div className="text-sm text-status-failed">
                无法连接到 Python 运行时
              </div>
              <div className="text-xs text-text-secondary">
                请确保已安装 Python 3.11+ 并配置了 API Key
              </div>
              <button
                type="button"
                onClick={() => {
                  setStatus('connecting');
                  setAttempts(0);
                  window.location.reload();
                }}
                className="rounded bg-chief px-4 py-2 text-sm text-white hover:bg-chief/90"
              >
                重试
              </button>
            </div>
          )}
        </div>

        {/* Progress bar */}
        <div className="w-64 overflow-hidden rounded-full bg-surface-3">
          <div
            className="h-1 bg-chief transition-all duration-500"
            style={{ width: `${Math.min(100, (attempts / MAX_ATTEMPTS) * 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
