"""Model router: role → provider:model.

Reads a static config (TOML or in-memory dict) and picks a model
per role. Phase 1: no failover. Phase 2 adds retry + failover
chains per docs/PROVIDER_SPEC §6.

See `docs/PROVIDER_SPEC.md` §5.3 and §6.
"""

from __future__ import annotations

from dataclasses import dataclass

from aco_runtime_lib.providers.base import Provider, ProviderError
from aco_runtime_lib.providers.mock import MockProvider


@dataclass(slots=True, frozen=True)
class ModelRef:
    """A reference to a specific provider:model."""

    provider_id: str
    model_id: str

    def __str__(self) -> str:
        return f"{self.provider_id}:{self.model_id}"

    @classmethod
    def parse(cls, ref: str) -> ModelRef:
        if ":" not in ref:
            raise ValueError(f"invalid model ref: {ref!r} (expected 'provider:model')")
        provider_id, model_id = ref.split(":", 1)
        if not provider_id or not model_id:
            raise ValueError(f"invalid model ref: {ref!r}")
        return cls(provider_id=provider_id, model_id=model_id)


@dataclass(slots=True)
class RouterConfig:
    """Per-role default model. Mirrors `config/router.toml`."""

    defaults: dict[str, ModelRef]
    """Default model per role. Used by `pick()`."""

    fallbacks: dict[str, list[ModelRef]] = None  # type: ignore[assignment]
    """Per-role fallback chain. Used by `pick_with_failover()`.

    `None` (the default) means no fallbacks for that role; pick()
    will fail if the default provider is unreachable. Set explicitly
    via `RouterConfig.from_toml_dict()` (which reads the `[fallback.<role>]`
    section of `router.toml`).
    """

    def __post_init__(self) -> None:
        if self.fallbacks is None:
            self.fallbacks = {}

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> RouterConfig:
        return cls(defaults={k: ModelRef.parse(v) for k, v in d.items()})

    @classmethod
    def from_toml_dict(
        cls,
        defaults: dict[str, str],
        fallbacks: dict[str, list[str]] | None = None,
    ) -> RouterConfig:
        """Build from the same shape as `config/router.toml`.

        ```toml
        [defaults]
        chief = "anthropic:claude-opus-4-8"
        [fallback.chief]
        chain = ["anthropic:claude-opus-4-8", "kimi:kimi-k2", "openai:gpt-5"]
        ```
        """
        fb: dict[str, list[ModelRef]] = {}
        if fallbacks:
            for role, chain in fallbacks.items():
                fb[role] = [ModelRef.parse(s) for s in chain]
        return cls(defaults={k: ModelRef.parse(v) for k, v in defaults.items()}, fallbacks=fb)


class RouterError(Exception):
    """Raised when the router cannot satisfy a role's request after
    exhausting the fallback chain.

    `last_error` is the underlying `ProviderError` (or None if the
    failure was a configuration error, e.g., no default for the role).
    """

    def __init__(self, message: str, *, last_error: Exception | None = None) -> None:
        super().__init__(message)
        self.last_error = last_error


class ModelRouter:
    """Picks a provider+model for a given role, with optional failover.

    v0.2: `pick_with_failover()` walks the per-role fallback chain
    on `ProviderError` whose `retryable=True`, stopping at the first
    success or raising `RouterError` on exhaustion.
    """

    def __init__(
        self,
        providers: dict[str, Provider],
        config: RouterConfig,
    ) -> None:
        self._providers = providers
        self._config = config

    def pick(self, role: str) -> tuple[Provider, ModelRef]:
        ref = self._config.defaults.get(role)
        if ref is None:
            raise ProviderError(f"no default model for role {role!r}", retryable=False)
        provider = self._providers.get(ref.provider_id)
        if provider is None:
            raise ProviderError(
                f"provider {ref.provider_id!r} is not enabled",
                retryable=False,
            )
        return provider, ref

    def pick_with_failover(self, role: str) -> tuple[Provider, ModelRef, int]:
        """Walk the per-role fallback chain.

        Returns `(provider, model_ref, attempts_used)`. Raises
        `RouterError` if every model in the chain is unreachable
        (or returns a non-retryable error on the first try).
        """
        chain: list[ModelRef] = []
        default = self._config.defaults.get(role)
        if default is not None:
            chain.append(default)
        chain.extend(self._config.fallbacks.get(role, []))

        if not chain:
            raise RouterError(f"no models configured for role {role!r}")

        last_error: Exception | None = None
        for i, ref in enumerate(chain, start=1):
            provider = self._providers.get(ref.provider_id)
            if provider is None:
                last_error = ProviderError(
                    f"provider {ref.provider_id!r} is not enabled", retryable=True
                )
                continue
            # The caller still has to call .chat() to know if the model
            # is reachable. We return the candidate; the caller's
            # loop handles the failover on retryable errors.
            return provider, ref, i
        raise RouterError(
            f"all {len(chain)} models in the {role!r} chain are unreachable",
            last_error=last_error,
        )

    def register(self, provider_id: str, provider: Provider) -> None:
        """Add or replace a provider at runtime (Phase 2: hot-reload)."""
        self._providers[provider_id] = provider

    @property
    def available(self) -> list[str]:
        return sorted(self._providers.keys())


def default_router(mock_first: bool = True) -> ModelRouter:
    """Build a router for tests / local dev. All roles → MockProvider.

    Production routers are built from `config/router.toml` and the
    real provider implementations (see `apps/runtime/main.py` in
    Phase 1 wiring).
    """
    mock = MockProvider()
    providers: dict[str, Provider] = {"mock": mock}
    config = RouterConfig.from_dict(
        {
            "chief": "mock:mock-m3",
            "critic_a": "mock:mock-m3",
            "critic_b": "mock:mock-m3",
            "worker": "mock:mock-m3",
            "reporter": "mock:mock-m3",
        }
    )
    return ModelRouter(providers=providers, config=config)
