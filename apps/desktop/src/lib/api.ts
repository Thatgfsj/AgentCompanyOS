/**
 * API client using Tauri's HTTP plugin to bypass webview CSP.
 */

import { fetch as tauriFetch } from '@tauri-apps/plugin-http';

const RUNTIME_URL = 'http://127.0.0.1:7317';

// ── Connection state ─────────────────────────────────────────────

type ConnectionState = 'unknown' | 'connected' | 'disconnected';

let _connectionState: ConnectionState = 'unknown';
let _lastHealthCheck = 0;
const HEALTH_CHECK_INTERVAL = 5000;

export function getConnectionState(): ConnectionState {
  return _connectionState;
}

export function isConnected(): boolean {
  return _connectionState === 'connected';
}

// ── Health check ─────────────────────────────────────────────────

export async function checkHealth(): Promise<boolean> {
  try {
    const r = await tauriFetch(`${RUNTIME_URL}/health`, {
      method: 'GET',
    });
    if (r.status === 200) {
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

export async function ensureConnected(maxRetries = 3): Promise<boolean> {
  if (Date.now() - _lastHealthCheck < HEALTH_CHECK_INTERVAL && _connectionState === 'connected') {
    return true;
  }
  for (let i = 0; i <= maxRetries; i++) {
    if (await checkHealth()) return true;
    if (i < maxRetries) await sleep(500 * Math.pow(2, i));
  }
  return false;
}

// ── Fetch helpers ────────────────────────────────────────────────

export async function fetchWithRetry(
  url: string,
  options: { method?: string; body?: unknown; retries?: number } = {},
): Promise<{ status: number; data: unknown }> {
  const { method = 'GET', body, retries = 2 } = options;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const fetchOptions: RequestInit = {
        method: method as 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
      };
      if (body !== undefined) {
        fetchOptions.body = JSON.stringify(body);
        fetchOptions.headers = { 'content-type': 'application/json' };
      }
      const r = await tauriFetch(url, fetchOptions);
      _connectionState = 'connected';
      let data: unknown = null;
      try {
        data = await (r as Response).json();
      } catch {
        // response might not have JSON body
      }
      return { status: r.status, data };
    } catch (err) {
      if (attempt < retries) {
        await sleep(1000 * Math.pow(2, attempt));
        continue;
      }
      _connectionState = 'disconnected';
      throw err;
    }
  }
  throw new Error('unreachable');
}

export async function getJson<T>(path: string): Promise<T> {
  const r = await fetchWithRetry(`${RUNTIME_URL}${path}`, { method: 'GET' });
  if (r.status < 200 || r.status >= 300) throw new Error(`HTTP ${r.status}`);
  return r.data as T;
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const r = await fetchWithRetry(`${RUNTIME_URL}${path}`, { method: 'POST', body });
  if (r.status < 200 || r.status >= 300) throw new Error(`HTTP ${r.status}`);
  return r.data as T;
}

export async function putJson<T>(path: string, body: unknown): Promise<T> {
  const r = await fetchWithRetry(`${RUNTIME_URL}${path}`, { method: 'PUT', body });
  if (r.status < 200 || r.status >= 300) throw new Error(`HTTP ${r.status}`);
  return r.data as T;
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

export function createWebSocket(path: string, options: WsOptions): () => void {
  const { onMessage, onOpen, onClose, onError, maxReconnects = 10, reconnectDelay = 1000 } = options;
  let ws: WebSocket | null = null;
  let reconnectCount = 0;
  let disposed = false;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  function connect() {
    if (disposed) return;
    try {
      ws = new WebSocket(`${RUNTIME_URL.replace('http', 'ws')}${path}`);
      ws.onopen = () => { reconnectCount = 0; onOpen?.(); };
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.kind === 'heartbeat') return;
          onMessage(data);
        } catch {
          // ignore
        }
      };
      ws.onclose = () => {
        onClose?.();
        if (!disposed && reconnectCount < maxReconnects) {
          reconnectCount++;
          const delay = Math.min(reconnectDelay * Math.pow(2, reconnectCount - 1), 10000);
          reconnectTimer = setTimeout(connect, delay);
        }
      };
      ws.onerror = (err) => { onError?.(err); };
    } catch {
      // ignore
    }
  }

  connect();
  return () => {
    disposed = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (ws) { ws.close(); ws = null; }
  };
}

// ── Polling helper ───────────────────────────────────────────────

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

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export { RUNTIME_URL };
