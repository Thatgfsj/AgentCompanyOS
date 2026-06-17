"""WebSocket endpoint for streaming workflow events to the Tauri webview.

Stub for Phase 0: echoes one ping then closes. Real impl in Phase 1.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/stream")
async def stream_events(websocket: WebSocket) -> None:
    """Stream WfEvent objects as JSON. Stub for Phase 0."""
    await websocket.accept()
    try:
        # Send a hello so the client can confirm the connection.
        await websocket.send_json(
            {
                "kind": "console",
                "agent_id": "agent:system",
                "level": "info",
                "message": "aco-runtime connected",
                "ts": datetime.now(UTC).isoformat(),
            }
        )
        # Keep the socket open; the real Phase 1 impl will push events
        # from the workflow engine's event bus.
        while True:
            await asyncio.sleep(60)
            await websocket.send_json(
                {
                    "kind": "console",
                    "agent_id": "agent:system",
                    "level": "debug",
                    "message": "heartbeat",
                    "ts": datetime.now(UTC).isoformat(),
                }
            )
    except WebSocketDisconnect:
        return
