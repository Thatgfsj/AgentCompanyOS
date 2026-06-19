"""Tests for the structured plugin system (Phase 2 / C).

Covers:
* Registry register / unregister / list / invoke
* Echo plugin round-trip
* Python plugin (inline source + timeout)
* Git plugin (read-only + confirm gating for write ops)
* Error normalization (unknown plugin, plugin exception, non-dict return)
"""
from __future__ import annotations

import asyncio
import os

import pytest

from aco_runtime_lib.plugins.base import Plugin, PluginRegistry, get_registry


# ── EchoPlugin ──────────────────────────────────────────────────


def test_echo_plugin_roundtrip() -> None:
    reg = PluginRegistry()
    from aco_runtime_lib.plugins.builtin.echo import EchoPlugin
    reg.register(EchoPlugin())
    result = asyncio.run(reg.invoke("echo", {"hello": "world"}))
    assert result["status"] == "ok"
    assert result["echoed"] == {"hello": "world"}


# ── PythonPlugin ────────────────────────────────────────────────


def test_python_inline_source_runs() -> None:
    reg = PluginRegistry()
    from aco_runtime_lib.plugins.builtin.python import PythonPlugin
    reg.register(PythonPlugin())
    result = asyncio.run(
        reg.invoke("python", {"code": "print(2 + 2)"})
    )
    assert result["status"] == "ok"
    assert result["exit_code"] == 0
    assert "4" in result["stdout"]


def test_python_requires_code_or_script() -> None:
    reg = PluginRegistry()
    from aco_runtime_lib.plugins.builtin.python import PythonPlugin
    reg.register(PythonPlugin())
    result = asyncio.run(reg.invoke("python", {}))
    assert result["status"] == "error"
    assert "code" in result["message"] or "script" in result["message"]


def test_python_rejects_both_code_and_script() -> None:
    reg = PluginRegistry()
    from aco_runtime_lib.plugins.builtin.python import PythonPlugin
    reg.register(PythonPlugin())
    result = asyncio.run(
        reg.invoke("python", {"code": "1", "script": "x.py"})
    )
    assert result["status"] == "error"


def test_python_timeout_returns_error() -> None:
    reg = PluginRegistry()
    from aco_runtime_lib.plugins.builtin.python import PythonPlugin
    reg.register(PythonPlugin())
    # Long-running sleep, very short timeout.
    result = asyncio.run(
        reg.invoke(
            "python",
            {"code": "import time; time.sleep(10)", "timeout_seconds": 0.5},
        )
    )
    assert result["status"] == "error"
    assert "timeout" in result["message"].lower()


# ── GitPlugin ───────────────────────────────────────────────────


def test_git_read_only_runs() -> None:
    reg = PluginRegistry()
    from aco_runtime_lib.plugins.builtin.git import GitPlugin
    reg.register(GitPlugin())
    result = asyncio.run(
        reg.invoke(
            "git",
            {"args": ["rev-parse", "--show-toplevel"]},
        )
    )
    assert result["status"] == "ok"
    assert result["write"] is False
    # stdout should be a directory
    assert os.path.isdir(result["stdout"].strip())


def test_git_write_requires_confirm() -> None:
    reg = PluginRegistry()
    from aco_runtime_lib.plugins.builtin.git import GitPlugin
    reg.register(GitPlugin())
    result = asyncio.run(reg.invoke("git", {"args": ["commit", "-m", "x"]}))
    assert result["status"] == "error"
    assert "confirm" in result["message"].lower()


def test_git_missing_args() -> None:
    reg = PluginRegistry()
    from aco_runtime_lib.plugins.builtin.git import GitPlugin
    reg.register(GitPlugin())
    result = asyncio.run(reg.invoke("git", {}))
    assert result["status"] == "error"
    assert "args" in result["message"]


# ── Registry behavior ───────────────────────────────────────────


def test_registry_unknown_plugin() -> None:
    reg = PluginRegistry()
    result = asyncio.run(reg.invoke("does-not-exist"))
    assert result["status"] == "error"
    assert "available" in result
    assert result["available"] == []


def test_registry_rejects_duplicate() -> None:
    reg = PluginRegistry()
    from aco_runtime_lib.plugins.builtin.echo import EchoPlugin
    reg.register(EchoPlugin())
    with pytest.raises(ValueError):
        reg.register(EchoPlugin())


def test_registry_rejects_empty_name() -> None:
    reg = PluginRegistry()

    class _NoName(Plugin):
        name = ""

        async def invoke(self, args, ctx=None):
            return {}

    with pytest.raises(ValueError):
        reg.register(_NoName())


def test_registry_normalizes_non_dict_return() -> None:
    """A buggy plugin returning a list should be wrapped, not
    propagated."""

    class _Bad(Plugin):
        name = "bad"

        async def invoke(self, args, ctx=None):
            return ["not", "a", "dict"]  # type: ignore[return-value]

    reg = PluginRegistry()
    reg.register(_Bad())
    result = asyncio.run(reg.invoke("bad"))
    assert result["status"] == "error"
    assert "non-dict" in result["message"]


def test_registry_catches_plugin_exception() -> None:
    class _Boom(Plugin):
        name = "boom"

        async def invoke(self, args, ctx=None):
            raise RuntimeError("kaboom")

    reg = PluginRegistry()
    reg.register(_Boom())
    result = asyncio.run(reg.invoke("boom"))
    assert result["status"] == "error"
    assert "kaboom" in result["message"]


def test_get_registry_singleton_has_builtins() -> None:
    reg = get_registry()
    names = {p.name for p in reg.list()}
    assert "echo" in names
    assert "python" in names
    assert "git" in names


def test_python_sandbox_does_not_inherit_secrets(monkeypatch) -> None:
    """Python plugin must NOT pass API keys from os.environ to the
    subprocess. Repro for the W2 finding: a Worker calling
    `python {"code": "import os; print(os.environ['MINIMAX_API_KEY'])"}`
    should NOT see the keychain-seeded secret."""
    import os
    from aco_runtime_lib.plugins.builtin.python import PythonPlugin

    # Pretend the lifespan already seeded a fake secret into env.
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-secret-should-not-leak")

    reg = PluginRegistry()
    reg.register(PythonPlugin())
    result = asyncio.run(
        reg.invoke(
            "python",
            {"code": "import os; print('KEY=' + os.environ.get('MINIMAX_API_KEY', '<missing>'))"},
        )
    )
    assert result["status"] == "ok"
    # The subprocess must see <missing>, not the secret.
    assert "KEY=<missing>" in result["stdout"], (
        f"python plugin leaked API key into subprocess: {result['stdout']!r}"
    )
    assert "sk-secret-should-not-leak" not in result["stdout"]


def test_python_sandbox_passes_explicit_allowlist(monkeypatch) -> None:
    """When the caller passes env_allowlist, those vars DO get
    inherited. Used to opt-in PATH extensions etc."""
    from aco_runtime_lib.plugins.builtin.python import PythonPlugin

    monkeypatch.setenv("MY_CUSTOM_VAR", "hello-from-parent")

    reg = PluginRegistry()
    reg.register(PythonPlugin())
    result = asyncio.run(
        reg.invoke(
            "python",
            {
                "code": "import os; print(os.environ.get('MY_CUSTOM_VAR', '<missing>'))",
                "env_allowlist": ["MY_CUSTOM_VAR"],
            },
        )
    )
    assert result["status"] == "ok"
    assert "hello-from-parent" in result["stdout"]


def test_python_sandbox_blocks_var_not_in_allowlist(monkeypatch) -> None:
    from aco_runtime_lib.plugins.builtin.python import PythonPlugin

    monkeypatch.setenv("SHOULD_NOT_LEAK", "secret")

    reg = PluginRegistry()
    reg.register(PythonPlugin())
    result = asyncio.run(
        reg.invoke(
            "python",
            {
                "code": "import os; print(os.environ.get('SHOULD_NOT_LEAK', '<missing>'))",
                "env_allowlist": ["PATH"],
            },
        )
    )
    assert "<missing>" in result["stdout"]


def test_git_apply_is_write_op() -> None:
    """W3 finding: 'apply' is missing from _READ_ONLY allowlist."""
    from aco_runtime_lib.plugins.builtin.git import GitPlugin
    reg = PluginRegistry()
    reg.register(GitPlugin())
    result = asyncio.run(reg.invoke("git", {"args": ["apply", "patch.diff"]}))
    assert result["status"] == "error"
    assert "confirm" in result["message"].lower()


def test_git_clean_requires_confirm() -> None:
    """`git clean -fdx` is destructive; must require confirm."""
    from aco_runtime_lib.plugins.builtin.git import GitPlugin
    reg = PluginRegistry()
    reg.register(GitPlugin())
    result = asyncio.run(
        reg.invoke("git", {"args": ["clean", "-fdx"]})
    )
    assert result["status"] == "error"
    assert "confirm" in result["message"].lower()


def test_git_reset_requires_confirm() -> None:
    from aco_runtime_lib.plugins.builtin.git import GitPlugin
    reg = PluginRegistry()
    reg.register(GitPlugin())
    result = asyncio.run(
        reg.invoke("git", {"args": ["reset", "--hard"]})
    )
    assert result["status"] == "error"
