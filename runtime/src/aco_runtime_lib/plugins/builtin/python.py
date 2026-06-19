"""Python plugin — run Python code or a script in a subprocess.

The Worker can call this with either:
  {"code": "print(1+1)"}      # inline source
  {"script": "scripts/x.py"}  # run a script file

Both are executed with the same Python interpreter as the runtime
(i.e. they inherit the runtime's env vars and packages). The
result captures stdout, stderr, and exit code.

Timeout
=======
Default 30s, override with `timeout_seconds`. The subprocess is
killed on timeout (SIGTERM, then SIGKILL after 5s grace).
"""
from __future__ import annotations

import asyncio
import os
import sys
import subprocess
from collections.abc import Mapping
from typing import Any

from aco_runtime_lib.plugins.base import Plugin


_DEFAULT_TIMEOUT = 30.0


_SANDBOX_ENV_BASE = {
    # Minimal env passed to the subprocess. By default we DO NOT
    # inherit any API keys or other secrets from os.environ — those
    # live in the OS keychain, accessible only via the runtime's
    # secrets API. A Worker that wants a key in a python script
    # must call back into the runtime via /api/settings/secrets/{n}/reveal
    # or pass the value explicitly as an arg (which the caller sees).
    "PATH": os.environ.get("PATH", ""),
    "PATHEXT": os.environ.get("PATHEXT", ""),
    "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
    "TEMP": os.environ.get("TEMP", ""),
    "TMP": os.environ.get("TMP", ""),
    "HOME": os.environ.get("HOME", os.environ.get("USERPROFILE", "")),
    "USERPROFILE": os.environ.get("USERPROFILE", ""),
    "LANG": os.environ.get("LANG", ""),
    "LC_ALL": os.environ.get("LC_ALL", ""),
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUNBUFFERED": "1",
}


def _sandbox_env(allowlist: object | None = None) -> dict[str, str]:
    """Build a sanitized env for the python subprocess.

    Args:
        allowlist: optional list of extra env var names to copy from
            the parent's os.environ. Useful for things like PATH
            extensions or PYTHONPATH the user explicitly wants the
            subprocess to see. **Names NOT in the base or the
            allowlist are NOT inherited**, so secrets like
            MINIMAX_API_KEY are not visible to the subprocess.

    Returns the dict to pass as `env=` to asyncio.create_subprocess_exec.
    """
    env = dict(_SANDBOX_ENV_BASE)
    if isinstance(allowlist, (list, tuple, set)):
        for name in allowlist:
            if not isinstance(name, str):
                continue
            value = os.environ.get(name)
            if value is not None:
                env[name] = value
    return env


class PythonPlugin(Plugin):
    name = "python"
    description = (
        "Execute Python source (args: {\"code\": \"...\"}) or a script file "
        "(args: {\"script\": \"path.py\"}) in a subprocess. "
        "Returns stdout, stderr, exit_code."
    )
    actions = ["exec"]

    async def invoke(
        self, args: Mapping[str, Any], ctx: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        code = args.get("code")
        script = args.get("script")
        if not code and not script:
            return {
                "status": "error",
                "message": "provide either 'code' or 'script' arg",
            }
        if code and script:
            return {
                "status": "error",
                "message": "provide only one of 'code' or 'script'",
            }

        cwd = args.get("cwd") or os.getcwd()
        timeout = float(args.get("timeout_seconds", _DEFAULT_TIMEOUT))
        sandbox_env = _sandbox_env(args.get("env_allowlist"))

        try:
            if code is not None:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-I",  # isolated mode: no user-site, no PYTHONPATH
                    "-c",
                    code,
                    cwd=cwd,
                    env=sandbox_env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(script),
                    cwd=cwd,
                    env=sandbox_env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
        except FileNotFoundError as exc:
            return {"status": "error", "message": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "error",
                "message": f"{type(exc).__name__}: {exc}",
            }

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "status": "error",
                "message": f"timeout after {timeout:.0f}s",
                "exit_code": None,
            }

        # Truncate huge outputs to keep JSON manageable.
        max_chars = int(args.get("max_output_chars", 10000))
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
        truncated = False
        if len(out) > max_chars:
            out = out[:max_chars] + f"... [truncated {len(out) - max_chars} chars]"
            truncated = True
        if len(err) > max_chars:
            err = err[:max_chars] + f"... [truncated {len(err) - max_chars} chars]"
            truncated = True

        return {
            "status": "ok" if proc.returncode == 0 else "error",
            "exit_code": proc.returncode,
            "stdout": out,
            "stderr": err,
            "truncated": truncated,
        }
