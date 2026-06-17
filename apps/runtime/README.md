# apps/runtime

Python AI runtime sidecar. FastAPI + uvicorn.

Launched by the Tauri shell via `tauri-plugin-shell`. Talks to the
desktop app over HTTP (RPC) and WebSocket (events).

## Develop

```bash
uv sync
uv run aco-runtime
```

The server listens on `127.0.0.1:7317` by default.

## Endpoints (Phase 0 stubs)

* `GET  /health` — liveness
* `POST /api/workflow` — start a workflow (501 in Phase 0)
* `GET  /api/workflow/{id}` — fetch a workflow (501 in Phase 0)
* `POST /api/workflow/{id}/cancel` — cancel (501 in Phase 0)
* `WS   /api/events/stream` — event stream (hello + heartbeat in Phase 0)

## Layout

```
apps/runtime/
├── pyproject.toml
├── README.md
└── src/aco_runtime/
    ├── main.py            ← uvicorn entry
    └── api/
        ├── schemas.py     ← Pydantic v2 models
        └── routes/
            ├── workflow.py
            └── events.py
```

See `docs/ARCHITECTURE.md` for the full runtime topology.
