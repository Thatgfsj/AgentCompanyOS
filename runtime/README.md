# runtime/

ACO AI runtime library. Production code path for the workflow engine.

The HTTP shell that exposes this library to the Tauri webview is
`apps/runtime/` (FastAPI + uvicorn).

## Layout

```
runtime/
├── pyproject.toml
├── src/aco_runtime_lib/
│   ├── __init__.py
│   ├── event_bus.py          # asyncio pub/sub
│   ├── workflow/             # state machine
│   ├── agents/               # Chief, Critics, Workers
│   ├── providers/            # LLM clients
│   ├── plugins/              # JSON-RPC over stdio
│   ├── prompts/              # template renderer
│   ├── memory/               # project memory
│   └── api/                  # placeholder
└── tests/
```

## Develop

```bash
uv sync
uv run pytest
```

## Phase status

| Module       | Phase 0 | Phase 1 | Phase 2 |
|--------------|---------|---------|---------|
| event_bus    | ✅      |         |         |
| workflow     | ✅ state machine | e2e e2e tests | DAG scheduler |
| agents       | ABCs    | real LLM calls | house-style |
| providers    | ABCs    | Anthropic      | 11 providers |
| plugins      | stub    | Python loader  | marketplace |
| prompts      | renderer| file loader    | A/B infra |
| memory       | in-mem  | SQLite-backed  | suggestion engine |

See `plans/Phase0.md` – `plans/Phase5.md` for the full plan.
