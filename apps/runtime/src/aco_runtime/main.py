"""FastAPI entry point for the Python AI runtime sidecar.

This process is launched by the Tauri shell (`tauri-plugin-shell`)
and communicates with the desktop app via:
  - HTTP for RPC (workflow start, plugin calls)
  - WebSocket for streaming events (workflow transitions, console)
  - JSON-RPC 2.0 over stdio for plugin IPC (the Tauri sidecar manages
    this for builtin plugins).

The actual workflow engine lives in the `runtime/` workspace member
(`runtime/workflow/...`). This file is the **thin** HTTP shell.
"""

from __future__ import annotations

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, WebSocket
from loguru import logger
from pydantic import BaseModel

from .api.routes.workflow import router as workflow_router
from .api.routes.events import router as events_router
from .api.schemas import HealthResponse

# ── Lifecycle ────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("aco-runtime starting up")
    yield
    logger.info("aco-runtime shutting down")


# ── App ──────────────────────────────────────────────────────────

app = FastAPI(
    title="Agent Company OS — Python Runtime",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness check; Tauri polls this on startup."""
    return HealthResponse(status="ok", version="0.1.0")


app.include_router(workflow_router, prefix="/api/workflow", tags=["workflow"])
app.include_router(events_router, prefix="/api/events", tags=["events"])


# ── Entry point ──────────────────────────────────────────────────


def main() -> None:
    """Run uvicorn. Defaults to 127.0.0.1:7317 to avoid clashes."""
    host = "127.0.0.1"
    port = 7317

    def _signal_handler(signum: int, _frame: object) -> None:
        logger.info("received signal {}", signum)
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    uvicorn.run(
        "aco_runtime.main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=False,
        reload=False,
    )


if __name__ == "__main__":
    main()
