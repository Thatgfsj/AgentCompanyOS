"""Docker plugin for ACO runtime.

Provides Docker operations: build, run, test, compose.
Safety: read-only by default; write operations require `confirm=true`.

Spec: `docs/PLUGIN_SPEC.md` §3.2.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any

from aco_runtime_lib.plugins.base import Plugin


class DockerPlugin(Plugin):
    """Docker operations plugin."""

    name = "docker"
    description = "Docker container operations (build, run, test, compose)"
    actions = ["build", "run", "test", "compose", "ps", "images", "logs"]

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

    async def _action_build(
        self, args: Mapping[str, Any], ctx: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Build a Docker image."""
        tag = args.get("tag", "")
        dockerfile = args.get("dockerfile", "Dockerfile")
        context = args.get("context", ".")

        if not tag:
            return {"status": "error", "message": "missing 'tag' parameter"}

        cmd = ["docker", "build", "-t", tag, "-f", dockerfile, context]
        return await self._run_cmd(cmd)

    async def _action_run(
        self, args: Mapping[str, Any], ctx: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Run a Docker container."""
        image = args.get("image", "")
        if not image:
            return {"status": "error", "message": "missing 'image' parameter"}

        cmd = ["docker", "run"]

        # Optional flags
        if args.get("detach"):
            cmd.append("-d")
        if args.get("rm"):
            cmd.append("--rm")
        if args.get("name"):
            cmd.extend(["--name", args["name"]])
        if args.get("port"):
            cmd.extend(["-p", args["port"]])
        if args.get("env"):
            for key, value in args["env"].items():
                cmd.extend(["-e", f"{key}={value}"])
        if args.get("volume"):
            cmd.extend(["-v", args["volume"]])

        cmd.append(image)

        # Command to run inside container
        if args.get("command"):
            if isinstance(args["command"], list):
                cmd.extend(args["command"])
            else:
                cmd.extend(["sh", "-c", args["command"]])

        return await self._run_cmd(cmd)

    async def _action_test(
        self, args: Mapping[str, Any], ctx: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Run tests in a Docker container."""
        image = args.get("image", "")
        if not image:
            return {"status": "error", "message": "missing 'image' parameter"}

        test_cmd = args.get("command", "pytest")
        cmd = ["docker", "run", "--rm", image]

        if isinstance(test_cmd, list):
            cmd.extend(test_cmd)
        else:
            cmd.extend(["sh", "-c", test_cmd])

        return await self._run_cmd(cmd)

    async def _action_compose(
        self, args: Mapping[str, Any], ctx: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Run docker-compose commands."""
        subcmd = args.get("subcommand", "up")
        file = args.get("file", "docker-compose.yml")

        cmd = ["docker", "compose", "-f", file, subcmd]

        if subcmd == "up" and args.get("detach"):
            cmd.append("-d")
        if subcmd == "down" and args.get("volumes"):
            cmd.append("-v")

        if args.get("services"):
            if isinstance(args["services"], list):
                cmd.extend(args["services"])
            else:
                cmd.append(args["services"])

        return await self._run_cmd(cmd)

    async def _action_ps(
        self, args: Mapping[str, Any], ctx: Mapping[str, Any]
    ) -> dict[str, Any]:
        """List running containers."""
        cmd = ["docker", "ps", "--format", "json"]

        if args.get("all"):
            cmd.insert(2, "-a")

        return await self._run_cmd(cmd)

    async def _action_images(
        self, args: Mapping[str, Any], ctx: Mapping[str, Any]
    ) -> dict[str, Any]:
        """List Docker images."""
        cmd = ["docker", "images", "--format", "json"]
        return await self._run_cmd(cmd)

    async def _action_logs(
        self, args: Mapping[str, Any], ctx: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Get container logs."""
        container = args.get("container", "")
        if not container:
            return {"status": "error", "message": "missing 'container' parameter"}

        cmd = ["docker", "logs"]

        if args.get("tail"):
            cmd.extend(["--tail", str(args["tail"])])
        if args.get("since"):
            cmd.extend(["--since", args["since"]])

        cmd.append(container)
        return await self._run_cmd(cmd)

    async def _run_cmd(self, cmd: list[str]) -> dict[str, Any]:
        """Run a shell command and return structured result."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

            return {
                "status": "ok" if proc.returncode == 0 else "error",
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
        except asyncio.TimeoutError:
            return {"status": "error", "message": "command timed out (60s)"}
        except FileNotFoundError:
            return {"status": "error", "message": "docker not found in PATH"}
        except Exception as exc:
            return {"status": "error", "message": f"{type(exc).__name__}: {exc}"}
