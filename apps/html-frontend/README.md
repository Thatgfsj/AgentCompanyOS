# Flowntier HTML Frontend (v0.4.21, event 000057)

A **portable**, **browser-runnable** shell for the Flowntier pipe
server. No Tauri, no bundler, no framework — just `index.html`
and `app.js` talking to the pipe server over loopback HTTP.

This exists so the chairman can drive Flowntier from **any
browser**, on any OS, including environments where the Tauri
desktop shell can't be built (clean macOS box, headless Linux
server, an embedded device, a different user account, or just
a quick `chrome.exe` from another workstation).

## Architecture

```
┌────────────────────────┐    HTTP+SSE (127.0.0.1:8765)    ┌──────────────────────┐
│  index.html + app.js   │ ───────────────────────────────►│  flowntier-runtime   │
│  (any browser)         │  POST /rpc                       │  ws_bridge.rs        │
│                        │  GET  /events (Server-Sent)     │                      │
│                        │  GET  /health                   │                      │
└────────────────────────┘ ◄───────────────────────────────└──────────────────────┘
                                                          (also named-pipe IPC
                                                           for the Tauri shell)
```

The wire format on the HTTP bridge is **identical** to the
named-pipe transport: same JSON-RPC envelope, same `AgentEvent`
serialisation, same `path` / `body` parameters. Handlers in
`crates/pipe-server/src/handlers.rs` are unchanged.

The bridge binds to **`127.0.0.1`** only — it is a local sidecar,
not a network service. Override via `FLOWNTIER_HTTP_BRIDGE`
environment variable (e.g. `FLOWNTIER_HTTP_BRIDGE=127.0.0.1:9000`).

## Running it

1. Start the pipe server:
   ```bash
   cargo run -p pipe-server --bin flowntier-runtime
   ```
   You should see `v0.4.21: HTTP+SSE bridge listening (loopback only)` in the log.

2. Open the frontend in any browser:
   ```bash
   cd apps/html-frontend
   python -m http.server 8000  # or any static file server
   # then open http://localhost:8000/index.html
   ```
   Or just double-click `index.html` — `fetch()` works from
   `file://` against loopback HTTP.

3. Type a message into the chat input, click 发送. The frontend
   POSTs `POST /api/run_task` to the bridge, the pipe server
   streams AgentEvents back over `/events`, and the transcript
   fills in live.

4. The right pane polls `GET /api/quota/status` every 15 s and
   shows the chairman-mandated quota state per `(role, model)`
   pair. Click **重置** on a `rate_limited` row to clear it.

## Switching language

Use the language picker in the header (中文 / English). The
choice persists in `localStorage`.

## CORS

The bridge responds with `Access-Control-Allow-Origin: *` and
handles `OPTIONS` preflight, so any browser, any origin, can
drive it. **Do not** expose port 8765 to the network — the
chairman should `ssh -L` tunnel if remote access is needed.

## What's intentionally NOT here

The Tauri desktop shell has ~1500 lines of provider-management
UI (toggle / patch / add custom / fetch model list / etc.). The
HTML frontend ships **only** ChatZone + Quota Status, because
the chairman's primary use case is "chat from anywhere" + "see
quota state without launching the desktop shell".

The provider-management endpoints (`GET /api/providers`,
`PATCH /api/providers/{id}`, `PUT /api/settings/secrets/{name}`,
`GET /api/router/roles`, `PUT /api/router/roles`, etc.) are all
already exposed via `POST /rpc` — you can drive them from the
browser devtools console:

```js
await rpc('GET', '/api/providers')
await rpc('PUT', '/api/router/roles', { roles: [{ role: 'agent:chief', default_model: 'minimax:MiniMax-Text-01', fallback_chain: [] }] })
```

A v0.5 follow-up will add a Settings pane to the HTML frontend
that wraps these calls in UI.