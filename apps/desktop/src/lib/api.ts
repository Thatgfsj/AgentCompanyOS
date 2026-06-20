/**
 * Robust API client with retry, health check, and connection management.
 *
 * All runtime API calls go through this module to ensure:
 * - Automatic retry on transient failures
 * - Health check before operations
 * - Connection status tracking
 * - Timeout handling
 */

const RUNTIME_URL = 'http://127.0.0.1:7317';

// ── Connection state ─────────────────────────────────────────────

type ConnectionState = 'unknown' | 'connected' | 'disconnected';

let _connectionState: ConnectionState = 'unknown';
let _lastHealthCheck = 0;
const HEALTH_CHECK_INTERVAL = 5000; // 5s

export function getConnectionState(): ConnectionState {
  return _connectionState;
}

export function isConnected(): boolean {
  return _connectionState === 'connected';
}

// ── Health check ─────────────────────────────────────────────────

export async function checkHealth(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);

    const r = await fetch(`${RUNTIME_URL}/health`, {
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (r.ok) {
      _connectionState = 'connected';
      _lastHealthCheck = Date.now();
      return true;
    }
  } catch {
    // ignore
  }

  _connectionState = 'disconnected';
  _lastHealthCheck = Date.now();
  return false;
}

/**
 * Ensure runtime is reachable. Retries up to `maxRetries` times with
 * exponential backoff. Returns true if connected, false if exhausted.
 */
export async function ensureConnected(maxRetries = 3): Promise<boolean> {
  // Skip if recently checked
  if (Date.now() - _lastHealthCheck < HEALTH_CHECK_INTERVAL && _connectionState === 'connected') {
    return true;
  }

  for (let i = 0; i <= maxRetries; i++) {
    if (await checkHealth()) return true;
    if (i < maxRetries) {
      await sleep(500 * Math.pow(2, i)); // 500ms, 1s, 2s
    }
  }
  return false;
}

// ── Fetch with retry ─────────────────────────────────────────────

interface FetchOptions extends RequestInit {
  retries?: number;
  retryDelay?: number;
  timeout?: number;
}

/**
 * Fetch with automatic retry on network errors and 5xx responses.
 */
export async function fetchWithRetry(
  url: string,
  options: FetchOptions = {},
): Promise<Response> {
  const {
    retries = 2,
    retryDelay = 1000,
    timeout = 30000,
    ...fetchOpts
  } = options;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(url, {
        ...fetchOpts,
        signal: controller.signal,
      });
      clearTimeout(timer);

      // Don't retry on 4xx (client errors)
      if (response.ok || (response.status >= 400 && response.status < 500)) {
        _connectionState = 'connected';
        return response;
      }

      // 5xx — retry
      if (attempt < retries) {
        console.warn(`[api] ${response.status} from ${url}, retrying (${attempt + 1}/${retries})...`);
        await sleep(retryDelay * Math.pow(2, attempt));
        continue;
      }

      _connectionState = 'connected';
      return response;
    } catch (err) {
      if (attempt < retries) {
        console.warn(`[api] fetch failed for ${url}, retrying (${attempt + 1}/${retries})...`, err);
        await sleep(retryDelay * Math.pow(2, attempt));
        continue;
      }
      _connectionState = 'disconnected';
      throw err;
    }
  }

  throw new Error('unreachable');
}

/**
 * Convenience: GET with retry, returns parsed JSON.
 */
export async function getJson<T>(path: string, opts?: FetchOptions): Promise<T> {
  const r = await fetchWithRetry(`${RUNTIME_URL}${path}`, {
    method: 'GET',
    ...opts,
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
  return r.json() as Promise<T>;
}

/**
 * Convenience: POST with retry, returns parsed JSON.
 */
export async function postJson<T>(path: string, body: unknown, opts?: FetchOptions): Promise<T> {
  const r = await fetchWithRetry(`${RUNTIME_URL}${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
    ...opts,
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
  return r.json() as Promise<T>;
}

/**
 * Convenience: PUT with retry.
 */
export async function putJson<T>(path: string, body: unknown, opts?: FetchOptions): Promise<T> {
  const r = await fetchWithRetry(`${RUNTIME_URL}${path}`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
    ...opts,
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
  return r.json() as Promise<T>;
}

/**
 * Convenience: PATCH with retry.
 */
export async function patchJson<T>(path: string, body: unknown, opts?: FetchOptions): Promise<T> {
  const r = await fetchWithRetry(`${RUNTIME_URL}${path}`, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
    ...opts,
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
  return r.json() as Promise<T>;
}

/**
 * Convenience: DELETE with retry.
 */
export async function deleteReq(path: string, opts?: FetchOptions): Promise<void> {
  const r = await fetchWithRetry(`${RUNTIME_URL}${path}`, {
    method: 'DELETE',
    ...opts,
  });
  if (!r.ok && r.status !== 404) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
}

// ── WebSocket with reconnect ─────────────────────────────────────

export interface WsOptions {
  onMessage: (data: unknown) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (err: Event) => void;
  maxReconnects?: number;
  reconnectDelay?: number;
}

/**
 * Create a WebSocket connection with automatic reconnect.
 * Returns a cleanup function.
 */
export function createWebSocket(path: string, options: WsOptions): () => void {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    maxReconnects = 10,
    reconnectDelay = 1000,
  } = options;

  let ws: WebSocket | null = null;
  let reconnectCount = 0;
  let disposed = false;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  function connect() {
    if (disposed) return;

    try {
      ws = new WebSocket(`${RUNTIME_URL.replace('http', 'ws')}${path}`);

      ws.onopen = () => {
        reconnectCount = 0;
        onOpen?.();
      };

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.kind === 'heartbeat') return;
          onMessage(data);
        } catch (e) {
          console.warn('[ws] bad message:', e);
        }
      };

      ws.onclose = () => {
        onClose?.();
        if (!disposed && reconnectCount < maxReconnects) {
          reconnectCount++;
          const delay = Math.min(reconnectDelay * Math.pow(2, reconnectCount - 1), 10000);
          console.warn(`[ws] disconnected, reconnecting in ${delay}ms (${reconnectCount}/${maxReconnects})`);
          reconnectTimer = setTimeout(connect, delay);
        }
      };

      ws.onerror = (err) => {
        onError?.(err);
      };
    } catch (e) {
      console.error('[ws] failed to connect:', e);
    }
  }

  connect();

  return () => {
    disposed = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (ws) {
      ws.close();
      ws = null;
    }
  };
}

// ── Polling helper ───────────────────────────────────────────────

/**
 * Poll a condition until it returns true or timeout.
 * Returns true if condition met, false if timed out.
 */
export async function pollUntil(
  condition: () => Promise<boolean>,
  options: { interval?: number; timeout?: number } = {},
): Promise<boolean> {
  const { interval = 1000, timeout = 60000 } = options;
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    if (await condition()) return true;
    await sleep(interval);
  }
  return false;
}

// ── Helpers ──────────────────────────────────────────────────────

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export { RUNTIME_URL };
