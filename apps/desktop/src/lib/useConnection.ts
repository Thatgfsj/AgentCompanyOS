/**
 * React hook for runtime connection status.
 * Periodically checks health and exposes connection state.
 */

import { useCallback, useEffect, useState } from 'react';
import { checkHealth, getConnectionState, ensureConnected } from './api.js';

export interface ConnectionStatus {
  connected: boolean;
  state: 'unknown' | 'connected' | 'disconnected';
  checking: boolean;
  retry: () => Promise<boolean>;
}

/**
 * Poll runtime health every `interval` ms.
 * Returns current connection state and a manual retry function.
 */
export function useConnection(interval = 5000): ConnectionStatus {
  const [connected, setConnected] = useState(false);
  const [checking, setChecking] = useState(false);

  const check = useCallback(async () => {
    setChecking(true);
    try {
      const ok = await checkHealth();
      setConnected(ok);
      return ok;
    } finally {
      setChecking(false);
    }
  }, []);

  const retry = useCallback(async () => {
    setChecking(true);
    try {
      const ok = await ensureConnected(5);
      setConnected(ok);
      return ok;
    } finally {
      setChecking(false);
    }
  }, []);

  // Initial check + periodic polling
  useEffect(() => {
    void check();
    const timer = setInterval(() => void check(), interval);
    return () => clearInterval(timer);
  }, [check, interval]);

  return {
    connected,
    state: getConnectionState(),
    checking,
    retry,
  };
}
