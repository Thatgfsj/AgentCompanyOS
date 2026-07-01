# Flowntier HTML Frontend (v0.4.21, event 000058)

A **portable**, **browser-runnable** shell for the Flowntier pipe
server. Wraps the **same React bundle that the Tauri desktop shell
ships** (`apps/desktop/dist/`) in a thin `window.__TAURI_INTERNALS__`
shim so the entire Settings + ChatZone + WorkdirSetup + quota
panel renders unchanged inside any browser, on any OS.

The chairman's requirement was "跟应用端一模一样的前端 Flowntier".
The shim approach is the answer: there is no second React
codebase, no parallel UI implementation. Just the desktop
bundle + a 30-line Tauri 2.x IPC shim that translates every
`__TAURI_INTERNALS__.invoke(cmd, args)` call into a POST /rpc
against the pipe server's HTTP bridge.

## How it works

```
┌─────────────────────────────────┐    HTTP+SSE (loopback)    ┌──────────────────────┐
│  dist/index.html                │ ───────────────────────► │  flowntier-runtime   │
│  ├─ dist/tauri-shim.js          │  POST /rpc                │  ws_bridge.rs        │
│  └─ dist/assets/index-*.js      │  GET  /events  (SSE)      │                      │
│     (the actual desktop bundle) │  GET  /health             │                      │
└─────────────────────────────────┘ ◄──────────────────────── └──────────────────────┘
```

* `dist/tauri-shim.js` installs `window.__TAURI_INTERNALS__` with
  three methods (`invoke`, `transformCallback`,
  `unregisterCallback`). Every invoke maps to a FastAPI-style
  `POST /rpc` against the bridge. Event subscriptions (`listen()`)
  are wired to the SSE stream.
* The shim has an explicit `CMD_MAP` (≈40 entries) that maps each
  Tauri command name (`list_providers`, `save_secret`,
  `get_role_resolve_status`, …) to its `(method, pathTemplate)`
  against the pipe server. Adding a new command = one row in the
  map.
* `dist/index.html` loads the shim FIRST, then the desktop
  bundle (`assets/index-B4g6M-ob.js`). The bundle calls into
  `__TAURI_INTERNALS__` exactly like the Tauri shell does — no
  code change in the desktop React codebase.

## Running it

1. Start the pipe-server with the HTTP bridge bound to a free
   loopback port. The default 8765 may collide with another
   service (Python MCP, dev tools); use 18765 if so:

   ```bash
   # pick a port that's free: netstat -ano | grep ":PORT"
   FLOWNTIER_HTTP_BRIDGE=127.0.0.1:18765 \
       /path/to/flowntier-runtime.exe
   ```

   Or copy the `flowntier-runtime.exe` shipped to your desktop
   and run it directly. (The NSIS-installed runtime at
   `O:\Flowntier\flowntier_runtime.exe` is the **v0.4.20**
   build — it doesn't ship the bridge, so the HTML frontend
   won't work until the chairman replaces it with the
   v0.4.21 runtime; see `~/Desktop/flowntier-runtime-v0.4.21.exe`.)

   You should see `[bridge] listening on 127.0.0.1:18765` in the
   console (stderr).

2. Open `dist/index.html` in any browser. The shim auto-discovers
   the bridge on `127.0.0.1:18765`; if you used a different
   port, set `localStorage.flnwttier.bridge = "http://127.0.0.1:NNNN"`
   in the browser devtools and reload.

3. The full Flowntier UI renders: language picker (zh-CN /
   en-US), role picker, chat input + transcript, Settings panel
   with provider management, secret editor, role assignments,
   quota status block, nudge banner, workdir setup. **Identical
   to the desktop bundle.**

## What shim translates

Tauri 2.x's `@tauri-apps/api/event` (`listen` / `emit` /
`once`) is implemented in terms of `__TAURI_INTERNALS__.invoke`
with cmd names `plugin:event|listen` / `plugin:event|unlisten`.
The shim intercepts those commands and wires them to the
`/events` SSE stream — each SSE message becomes a fan-out to
every `listen()` subscriber. `transformCallback(cb)` allocates a
local id and stores the JS callback in a map; when SSE delivers
an AgentEvent, the shim looks up the callback by id and invokes
it with `{event, payload}` exactly like Tauri's main thread
would.

## CORS

The bridge responds with `Access-Control-Allow-Origin: *` and
handles `OPTIONS` preflight. The HTML frontend can therefore be
served from any origin (or from `file://`) and still drive the
loopback bridge.

## Why we don't reuse the named-pipe transport

Browsers can't read named pipes (`\\.\pipe\...`) or Unix domain
sockets. Period. That's why we built the HTTP bridge at all.
The desktop bundle was happy with named pipes; the browser host
needs HTTP. The shim bridges the gap on the browser side without
needing pipe-server or the desktop shell to change.

## What's NOT here (deferred to v0.5)

* WorkdirSetup flows that rely on Tauri's `dialog` plugin
  (file pickers). The HTML frontend can drive workdir setting
  via `set_workdir(path)` (the shim handles this), but the file
  picker dialog has to be a plain HTML `<input type="file">`
  that we'll add when needed.

* Native menus, native notifications. These are Tauri-side
  concerns that don't translate to a browser tab.