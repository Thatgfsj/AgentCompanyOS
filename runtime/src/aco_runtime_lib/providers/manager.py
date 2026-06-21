"""ProviderManager — in-memory registry for the v0.2 demo.

Responsibilities:
* Hold the **current** set of providers (id, enabled, env var set, etc.)
* Map enabled provider ids → live `Provider` instances
* Hand a `ModelRouter` to the rest of the runtime
* Survive user config changes (rebuild on demand)

The persistent source of truth (per `docs/CONFIG.md` §2) is TOML on
disk; for the v0.2 demo we keep state in memory and let the UI
mutate it. Restarting the runtime clears everything.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from aco_runtime_lib.providers.anthropic import AnthropicProvider
from aco_runtime_lib.providers.base import Provider
from aco_runtime_lib.providers.google import GoogleProvider  # noqa: F401  (may be absent)
from aco_runtime_lib.providers.minimax import MiniMaxProvider
from aco_runtime_lib.providers.mock import MockProvider
from aco_runtime_lib.providers.openai import OpenAIProvider
from aco_runtime_lib.providers.presets import (
    PROVIDER_PRESETS,
    PresetModel,
    ProviderPreset,
    get_preset,
)
from aco_runtime_lib.providers.router import (
    ModelRouter,
    RouterConfig,
)


@dataclass(slots=True)
class ProviderStatus:
    id: str
    display_name: str
    kind: str
    base_url: str
    api_key_env: str
    enabled: bool
    key_present: bool
    """Whether the env var named in `api_key_env` is currently set."""
    is_local: bool
    notes: str
    models: list[PresetModel] = field(default_factory=list)


@dataclass(slots=True)
class RoleAssignment:
    role: str
    default_model: str  # "provider:model"
    fallback_chain: list[str] = field(default_factory=list)


def _is_key_present(env_var: str, is_local: bool) -> bool:
    """True if the env var is set to a non-empty value.

    For local providers (Ollama, LM Studio) the env var is a
    placeholder like `OLLAMA_NO_KEY`; we accept any non-empty value.
    """
    val = os.environ.get(env_var, "")
    if is_local:
        # For local providers, accept any non-empty value (the value
        # is sent to a server that ignores it, but the env var must
        # be set to *something* so the Provider constructor doesn't
        # raise).
        return val.strip() != ""
    return val.strip() != ""


def _build_provider(
    provider_id: str,
    kind: str,
    base_url: str,
    api_key_env: str,
    is_local: bool = False,
) -> Provider:
    """Construct a live `Provider` for either a preset or a custom entry.

    The API key is read from the env var on each construction;
    we don't cache it.
    """
    api_key = os.environ.get(api_key_env, "")
    if not _is_key_present(api_key_env, is_local):
        raise RuntimeError(
            f"env var {api_key_env!r} is not set; "
            f"provider {provider_id!r} cannot be initialized"
        )
    if kind == "anthropic":
        return AnthropicProvider(api_key=api_key, base_url=base_url)
    if kind == "openai":
        return OpenAIProvider(api_key=api_key, base_url=base_url)
    if kind == "google":
        from aco_runtime_lib.providers.google import GoogleProvider
        return GoogleProvider(api_key=api_key, base_url=base_url)
    if kind == "openai_compat":
        # Generic OpenAI-compat client (works for MiniMax, Kimi, DeepSeek,
        # OpenRouter, OneAPI, allpaca, user-defined relays, …).
        return MiniMaxProvider(api_key=api_key, base_url=base_url)
    raise RuntimeError(f"unknown provider kind: {kind}")


class ProviderManager:
    """In-memory registry. Thread-safe under asyncio (we use a lock)."""

    DEFAULT_ROLES: dict[str, str] = {
        "chief": "minimax:minimax-m3",
        "critic_a": "minimax:minimax-m3",
        "critic_b": "minimax:minimax-m3",
        "worker": "minimax:minimax-m3",
        "reporter": "minimax:minimax-m3",
    }

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        # provider_id -> {enabled, base_url, api_key_env, models}
        self._config: dict[str, dict[str, Any]] = {}
        # Custom user-defined providers (relay stations, private gateways, …)
        # Not in PROVIDER_PRESETS; persisted to disk by `_load_custom()`
        # on startup and written back by `save_custom()`.
        self._custom: dict[str, dict[str, Any]] = {}
        self._role_defaults: dict[str, str] = dict(self.DEFAULT_ROLES)
        self._fallback_chains: dict[str, list[str]] = {}
        # Cache the built ModelRouter — first build is slow (~5s per
        # provider on Windows due to httpx DNS resolution); subsequent
        # calls return the same instance. Use `invalidate_router()` to
        # force a rebuild after `apply_config()`.
        self._cached_router: ModelRouter | None = None
        self._init_defaults()
        self._load_custom()

    def _init_defaults(self) -> None:
        """Seed every preset as enabled if its key is present in env."""
        for preset in PROVIDER_PRESETS:
            enabled = _is_key_present(preset.api_key_env, preset.is_local)
            self._config[preset.id] = {
                "enabled": enabled,
                "base_url": preset.base_url,
                "api_key_env": preset.api_key_env,
                "models": [self._model_to_dict(m) for m in preset.default_models],
            }
        # Sensible default fallback chains
        self._fallback_chains = {
            "chief": [
                "anthropic:claude-opus-4-8",
                "openai:gpt-5",
                "minimax:minimax-m3",
            ],
            "critic_a": [
                "google:gemini-2-5-pro",
                "minimax:minimax-m3",
            ],
            "critic_b": [
                "anthropic:claude-sonnet-4-6",
                "minimax:minimax-m3",
            ],
            "worker": [
                "minimax:minimax-m3",
                "deepseek:deepseek-chat",
            ],
            "reporter": [
                "deepseek:deepseek-reasoner",
                "minimax:minimax-m3",
            ],
        }

    @staticmethod
    def _model_to_dict(m: PresetModel) -> dict[str, Any]:
        return {
            "id": m.id,
            "display_name": m.display_name,
            "context_window": m.context_window,
            "max_output_tokens": m.max_output_tokens,
            "input_cost_mtok": m.input_cost_mtok,
            "output_cost_mtok": m.output_cost_mtok,
            "capabilities": list(m.capabilities),
        }

    # ── Read API ────────────────────────────────────────────────

    def list_providers(self) -> list[ProviderStatus]:
        out: list[ProviderStatus] = []
        # Built-in presets first (so the UI shows the curated catalog).
        for preset in PROVIDER_PRESETS:
            cfg = self._config[preset.id]
            key_present = _is_key_present(preset.api_key_env, preset.is_local)
            enabled = bool(cfg["enabled"]) and key_present
            out.append(
                ProviderStatus(
                    id=preset.id,
                    display_name=preset.display_name,
                    kind=preset.kind,
                    base_url=str(cfg["base_url"]),
                    api_key_env=str(cfg["api_key_env"]),
                    enabled=enabled,
                    key_present=key_present,
                    is_local=preset.is_local,
                    notes=preset.notes,
                    models=[PresetModel(**m) for m in cfg["models"]],
                )
            )
        # Then user-defined custom providers (relay stations, private gateways).
        for cid, cfg in self._custom.items():
            key_present = _is_key_present(cfg["api_key_env"], False)
            out.append(
                ProviderStatus(
                    id=cid,
                    display_name=str(cfg["display_name"]),
                    kind=str(cfg["kind"]),
                    base_url=str(cfg["base_url"]),
                    api_key_env=str(cfg["api_key_env"]),
                    enabled=bool(cfg.get("enabled", True)) and key_present,
                    key_present=key_present,
                    is_local=False,
                    notes="Custom relay / private gateway",
                    models=[PresetModel(**m) for m in cfg.get("models", [])],
                )
            )
        return out

    def get_provider(self, provider_id: str) -> ProviderStatus | None:
        for p in self.list_providers():
            if p.id == provider_id:
                return p
        return None

    def list_roles(self) -> list[RoleAssignment]:
        return [
            RoleAssignment(
                role=role,
                default_model=self._role_defaults.get(role, "minimax:minimax-m3"),
                fallback_chain=list(self._fallback_chains.get(role, [])),
            )
            for role in ("chief", "critic_a", "critic_b", "worker", "reporter")
        ]

    def list_models_for_role(self, role: str) -> list[tuple[str, str]]:
        """Return [(provider_id, model_id), ...] for every enabled provider.

        Used by the UI to populate the role-assignment dropdowns.
        """
        out: list[tuple[str, str]] = []
        for p in self.list_providers():
            if not p.enabled:
                continue
            for m in p.models:
                out.append((p.id, m.id))
        return out

    # ── Write API ───────────────────────────────────────────────

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> None:
        if provider_id not in self._config:
            raise KeyError(f"unknown provider: {provider_id}")
        self._config[provider_id]["enabled"] = enabled

    def set_role_default(self, role: str, model_ref: str) -> None:
        if ":" not in model_ref:
            raise ValueError(f"model_ref must be 'provider:model', got {model_ref!r}")
        self._role_defaults[role] = model_ref

    def set_fallback_chain(self, role: str, chain: list[str]) -> None:
        for ref in chain:
            if ":" not in ref:
                raise ValueError(f"fallback chain entries must be 'provider:model', got {ref!r}")
        self._fallback_chains[role] = list(chain)

    # ── Custom (user-defined) providers ──────────────────────────
    #
    # Relay stations, private gateways, etc. — anything outside the
    # curated `PROVIDER_PRESETS` catalog. Persisted to
    # `~/.aco/custom_providers.json` so the user doesn't have to re-add
    # them after every restart.

    _CUSTOM_PATH = os.path.join(
        os.path.expanduser("~"), ".aco", "custom_providers.json"
    )

    def _load_custom(self) -> None:
        if not os.path.isfile(self._CUSTOM_PATH):
            return
        try:
            with open(self._CUSTOM_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for cid, cfg in (data or {}).items():
                self._custom[cid] = cfg
            logger.info("loaded {} custom provider(s) from {}", len(self._custom), self._CUSTOM_PATH)
        except Exception as e:  # noqa: BLE001
            logger.warning("failed to load custom providers: {}", e)

    def save_custom(self) -> None:
        os.makedirs(os.path.dirname(self._CUSTOM_PATH), exist_ok=True)
        with open(self._CUSTOM_PATH, "w", encoding="utf-8") as f:
            json.dump(self._custom, f, ensure_ascii=False, indent=2)

    def register_custom(
        self,
        provider_id: str,
        display_name: str,
        kind: str,
        base_url: str,
        api_key_env: str,
        models: list[dict] | None = None,
    ) -> None:
        if provider_id in {p.id for p in PROVIDER_PRESETS}:
            raise ValueError(
                f"id {provider_id!r} clashes with a built-in preset; pick another"
            )
        if kind not in ("anthropic", "openai", "openai_compat"):
            raise ValueError(
                f"kind must be anthropic | openai | openai_compat, got {kind!r}"
            )
        if not base_url.startswith(("http://", "https://")):
            raise ValueError(f"base_url must start with http:// or https://, got {base_url!r}")
        if not api_key_env or not api_key_env.replace("_", "").isalnum():
            raise ValueError(f"api_key_env must be alphanumeric+underscores, got {api_key_env!r}")
        # Normalize models to PresetModel-shaped dicts.
        norm_models: list[dict] = []
        for m in models or []:
            norm_models.append({
                "id": m["id"],
                "display_name": m.get("display_name") or m["id"],
                "context_window": int(m.get("context_window", 8192)),
                "max_output_tokens": int(m.get("max_output_tokens", 4096)),
                "input_cost_mtok": float(m.get("input_cost_mtok", 0.0)),
                "output_cost_mtok": float(m.get("output_cost_mtok", 0.0)),
                "capabilities": tuple(m.get("capabilities", ("chat", "stream", "json_mode"))),
            })
        self._custom[provider_id] = {
            "display_name": display_name,
            "kind": kind,
            "base_url": base_url,
            "api_key_env": api_key_env,
            "models": norm_models,
            "enabled": True,
        }
        self.invalidate_router()
        self.save_custom()

    def remove_custom(self, provider_id: str) -> None:
        if provider_id not in self._custom:
            raise KeyError(f"unknown custom provider: {provider_id!r}")
        del self._custom[provider_id]
        self.invalidate_router()
        self.save_custom()

    def is_custom(self, provider_id: str) -> bool:
        return provider_id in self._custom

    # ── Build a router from the current state ──────────────────

    def build_router(self) -> ModelRouter:
        """Construct a `ModelRouter` from the current configuration.

        Providers whose key is missing or whose entry is disabled are
        silently skipped.

        The result is **cached** — the first call constructs the
        providers (each opening an httpx.AsyncClient, which on
        Windows can take ~5s per provider due to DNS resolution),
        and subsequent calls return the same instance. The
        providers are stateless and safe to share across workflows.
        Call `invalidate_router()` after `apply_config()` to
        rebuild.
        """
        if self._cached_router is not None:
            return self._cached_router
        providers: dict[str, Provider] = {}
        for status in self.list_providers():
            if not status.enabled:
                continue
            try:
                if status.id in self._custom:
                    cfg = self._custom[status.id]
                    providers[status.id] = _build_provider(
                        status.id, cfg["kind"], cfg["base_url"],
                        cfg["api_key_env"], is_local=False,
                    )
                else:
                    preset = get_preset(status.id)
                    if preset is None:
                        continue
                    providers[status.id] = _build_provider(
                        preset.id, preset.kind, preset.base_url,
                        preset.api_key_env, is_local=preset.is_local,
                    )
            except RuntimeError:
                # Key missing at construction time — skip.
                continue
        if not providers:
            # Fall back to Mock so the runtime still works for demos.
            providers["mock"] = MockProvider()
        cfg = RouterConfig.from_toml_dict(
            defaults=self._role_defaults,
            fallbacks=self._fallback_chains,
        )
        self._cached_router = ModelRouter(providers=providers, config=cfg)
        return self._cached_router

    def invalidate_router(self) -> None:
        """Drop the cached router so the next build_router rebuilds.

        Call after `apply_config()` to pick up new provider settings.
        """
        self._cached_router = None

    def available_providers(self) -> list[str]:
        return [p.id for p in self.list_providers() if p.enabled]

    def has_any_provider(self) -> bool:
        return any(p.enabled for p in self.list_providers())
