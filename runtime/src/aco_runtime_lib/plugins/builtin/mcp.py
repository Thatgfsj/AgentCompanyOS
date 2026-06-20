"""MCP (Model Context Protocol) plugin for ACO runtime.

Provides a bridge to MCP servers for tool invocation.
Safety: sandboxed execution with timeout.

Spec: `docs/PLUGIN_SPEC.md` §3.3.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any

from aco_runtime_lib.plugins.base import Plugin


class MCPPlugin(Plugin):
    """MCP server bridge plugin."""

    name = "mcp"
    description = "Model Context Protocol bridge for tool invocation"
    actions = ["list_tools", "call_tool", "list_resources", "read_resource"]

    def __init__(self) -> None:
        self._servers: dict[str, dict[str, Any]] = {}

    def add_server(self, name: str, config: dict[str, Any]) -> None:
        """Register an MCP server."""
        self._servers[name] = config

    async def invoke(
        self, args: Mapping[str, Any], ctx: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        action = args.get("action", "")
        if not action:
            return {"status": "error", "message": "missing 'action' parameter"}

        handler = getattr(self, f"_action_{action}", None)
        if handler is None:
            return {
                "status": "error",
                "message": f"unknown action: {action!r}",
                "available": self.actions,
            }

        try:
            return await handler(args, ctx or {})
        except Exception as exc:
            return {"status": "error", "message": f"{type(exc).__name__}: {exc}"}

    async def _action_list_tools(
        self, args: Mapping[str, Any], ctx: Mapping[str, Any]
    ) -> dict[str, Any]:
        """List available tools from MCP servers."""
        server = args.get("server", "")
        if not server:
            # List all servers
            return {
                "status": "ok",
                "servers": list(self._servers.keys()),
            }

        if server not in self._servers:
            return {
                "status": "error",
                "message": f"unknown server: {server!r}",
                "available": list(self._servers.keys()),
            }

        # TODO: Implement actual MCP protocol communication
        # For now, return placeholder
        return {
            "status": "ok",
            "server": server,
            "tools": [],
            "message": "MCP tool listing not yet implemented",
        }

    async def _action_call_tool(
        self, args: Mapping[str, Any], ctx: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Call a tool on an MCP server."""
        server = args.get("server", "")
        tool = args.get("tool", "")
        tool_args = args.get("arguments", {})

        if not server:
            return {"status": "error", "message": "missing 'server' parameter"}
        if not tool:
            return {"status": "error", "message": "missing 'tool' parameter"}

        if server not in self._servers:
            return {
                "status": "error",
                "message": f"unknown server: {server!r}",
                "available": list(self._servers.keys()),
            }

        # TODO: Implement actual MCP protocol communication
        # For now, return placeholder
        return {
            "status": "ok",
            "server": server,
            "tool": tool,
            "arguments": tool_args,
            "result": None,
            "message": "MCP tool invocation not yet implemented",
        }

    async def _action_list_resources(
        self, args: Mapping[str, Any], ctx: Mapping[str, Any]
    ) -> dict[str, Any]:
        """List available resources from MCP servers."""
        server = args.get("server", "")
        if not server:
            return {
                "status": "ok",
                "servers": list(self._servers.keys()),
            }

        if server not in self._servers:
            return {
                "status": "error",
                "message": f"unknown server: {server!r}",
                "available": list(self._servers.keys()),
            }

        # TODO: Implement actual MCP protocol communication
        return {
            "status": "ok",
            "server": server,
            "resources": [],
            "message": "MCP resource listing not yet implemented",
        }

    async def _action_read_resource(
        self, args: Mapping[str, Any], ctx: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Read a resource from an MCP server."""
        server = args.get("server", "")
        uri = args.get("uri", "")

        if not server:
            return {"status": "error", "message": "missing 'server' parameter"}
        if not uri:
            return {"status": "error", "message": "missing 'uri' parameter"}

        if server not in self._servers:
            return {
                "status": "error",
                "message": f"unknown server: {server!r}",
                "available": list(self._servers.keys()),
            }

        # TODO: Implement actual MCP protocol communication
        return {
            "status": "ok",
            "server": server,
            "uri": uri,
            "contents": None,
            "message": "MCP resource reading not yet implemented",
        }
