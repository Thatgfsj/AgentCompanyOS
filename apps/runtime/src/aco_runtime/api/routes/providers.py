"""Provider + router config endpoints.

GET    /api/providers                       — list all known providers + status
GET    /api/providers/{id}                  — single provider status
PATCH  /api/providers/{id}                  — enable/disable a provider
POST   /api/providers/{id}/test             — test connection (model list ping)
GET    /api/providers/{id}/models           — pull live model list from the
                                                provider's API (Anthropic,
                                                OpenAI-compat, Gemini, Ollama,
                                                LM Studio)
POST   /api/providers/custom               — register a user-defined provider
                                                (relay station, private
                                                gateway). Persists across
                                                restarts. Body:
                                                {id, display_name, kind,
                                                 base_url, api_key_env,
                                                 models?}
DELETE /api/providers/custom/{id}          — drop a user-defined provider
GET   /api/router/roles                     — current role → model assignments
PUT   /api/router/roles                     — replace all assignments at once
GET   /api/models                           — every available model across enabled providers
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from loguru import logger

from aco_runtime_lib.providers import (
    PROVIDER_PRESETS,
    ProviderManager,
    ProviderStatus,
    RoleAssignment,
    get_preset,
)

router = APIRouter()

# ── Shared state ──────────────────────────────────────────────────

_manager: ProviderManager | None = None


def bind_manager(manager: ProviderManager) -> None:
    global _manager
    _manager = manager


def _m() -> ProviderManager:
    if _manager is None:
        raise HTTPException(status_code=503, detail="provider manager not ready")
    return _manager


# ── Serialization ────────────────────────────────────────────────


def _serialize_status(s: ProviderStatus) -> dict[str, Any]:
    return {
        "id": s.id,
        "display_name": s.display_name,
        "kind": s.kind,
        "base_url": s.base_url,
        "api_key_env": s.api_key_env,
        "enabled": s.enabled,
        "key_present": s.key_present,
        "is_local": s.is_local,
        "notes": s.notes,
        "models": [
            {
                "id": m.id,
                "display_name": m.display_name,
                "context_window": m.context_window,
                "max_output_tokens": m.max_output_tokens,
                "input_cost_mtok": m.input_cost_mtok,
                "output_cost_mtok": m.output_cost_mtok,
                "capabilities": list(m.capabilities),
            }
            for m in s.models
        ],
    }


def _serialize_role(r: RoleAssignment) -> dict[str, Any]:
    return {
        "role": r.role,
        "default_model": r.default_model,
        "fallback_chain": list(r.fallback_chain),
    }


# ── Endpoints ────────────────────────────────────────────────────


@router.get("")
async def list_providers() -> dict[str, Any]:
    m = _m()
    statuses = m.list_providers()
    return {
        "providers": [_serialize_status(s) for s in statuses],
        "roles": [_serialize_role(r) for r in m.list_roles()],
    }


@router.get("/{provider_id}")
async def get_provider(provider_id: str) -> dict[str, Any]:
    m = _m()
    s = m.get_provider(provider_id)
    if s is None:
        raise HTTPException(status_code=404, detail="provider not found")
    return _serialize_status(s)


@router.patch("/{provider_id}")
async def patch_provider(provider_id: str, body: dict[str, Any]) -> dict[str, Any]:
    m = _m()
    if provider_id not in [p.id for p in PROVIDER_PRESETS]:
        raise HTTPException(status_code=404, detail="unknown provider")
    if "enabled" in body:
        m.set_provider_enabled(provider_id, bool(body["enabled"]))
    s = m.get_provider(provider_id)
    if s is None:
        raise HTTPException(status_code=404, detail="provider not found")
    logger.info("provider {} enabled={}", provider_id, s.enabled)
    return _serialize_status(s)


@router.post("/{provider_id}/test")
async def test_provider(provider_id: str) -> dict[str, Any]:
    """Try to list models at the provider's base URL.

    For Anthropic/Gemini we don't have a list endpoint, so we
    return a synthetic success if the key is present and the URL
    is well-formed. For OpenAI-compatible providers we hit
    `/models` and check the response.
    """
    preset = get_preset(provider_id)
    if preset is None:
        raise HTTPException(status_code=404, detail="unknown provider")
    if not preset.base_url:
        return {"ok": False, "reason": "base_url is empty"}

    if preset.kind in ("anthropic", "google"):
        # No /models endpoint; just check the env var + URL shape.
        return {
            "ok": True,
            "reason": "no list endpoint for this provider; env var and URL OK",
            "base_url": preset.base_url,
        }

    # OpenAI-compatible: hit /models
    api_key = os.environ.get(preset.api_key_env, "") if preset.api_key_env else ""
    if not api_key and not preset.is_local:
        return {
            "ok": False,
            "reason": f"env var {preset.api_key_env!r} is empty",
        }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{preset.base_url.rstrip('/')}/models",
                headers={"authorization": f"Bearer {api_key}"} if api_key else {},
            )
        return {
            "ok": resp.status_code < 400,
            "status": resp.status_code,
            "model_count": (
                len(resp.json().get("data", [])) if resp.status_code < 400 else 0
            ),
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"connection error: {e}"}


import os  # noqa: E402  (imported here because `test_provider` uses it)


# ── Custom (user-defined) providers ──────────────────────────────


@router.post("/custom")
async def add_custom_provider(body: dict[str, Any]) -> dict[str, Any]:
    """Register a user-defined provider (relay station, private gateway).

    Persists to ~/.aco/custom_providers.json so the provider survives
    sidecar restarts. The custom provider appears in `list_providers()`
    with `notes="Custom relay / private gateway"` and can be picked
    in role assignments like any preset.
    """
    m = _m()
    try:
        m.register_custom(
            provider_id=str(body["id"]).strip(),
            display_name=str(body.get("display_name") or body["id"]).strip(),
            kind=str(body["kind"]).strip(),
            base_url=str(body["base_url"]).strip(),
            api_key_env=str(body["api_key_env"]).strip(),
            models=body.get("models") or [],
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    logger.info("custom provider registered: {}", body["id"])
    s = m.get_provider(body["id"])
    return _serialize_status(s) if s else {"ok": True}


@router.delete("/custom/{provider_id}")
async def remove_custom_provider(provider_id: str) -> dict[str, Any]:
    m = _m()
    try:
        m.remove_custom(provider_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    logger.info("custom provider removed: {}", provider_id)
    return {"ok": True}


# ── Live model-list pull ─────────────────────────────────────────


# How to ask each provider for its model catalog. Endpoint paths and
# response shapes are per-provider; key off `provider_id` first (specific
# overrides like Ollama) and fall back to `kind` for the generic groups.
# Each entry returns `(models: list[{id, display_name}], raw_error: str | None)`.
#
# `spec` is a duck-typed object exposing `.id`, `.kind`, `.base_url`. Both
# `ProviderPreset` (built-in) and a small ad-hoc namespace built from a
# custom-provider dict satisfy this shape, so the same dispatcher works
# for presets and user-defined relays.
def _fetch_live_models(
    spec: Any, api_key: str
) -> tuple[list[dict[str, Any]], str | None]:
    base = spec.base_url.rstrip("/")

    headers: dict[str, str] = {}
    if api_key:
        # Most providers take `Authorization: Bearer <key>`. Anthropic also
        # requires `anthropic-version`. Gemini puts the key in the query.
        if spec.kind == "anthropic":
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {api_key}"

    # Endpoint URL per provider. For custom providers we don't have an
    # id-specific override (no Ollama-style "/api/tags" hint), so we
    # dispatch purely on `kind`.
    if spec.id == "ollama":
        # Ollama exposes /api/tags (NOT /v1/models)
        url = base.rsplit("/v1", 1)[0] + "/api/tags"
    elif spec.id == "google":
        # Gemini: key in query
        url = f"{base}/v1beta/models?key={api_key}"
    elif spec.kind == "anthropic":
        url = f"{base}/v1/models"
    elif spec.kind == "google":
        # Custom provider claiming google kind — use the same Gemini
        # shape with the key in the query string.
        url = f"{base}/v1beta/models?key={api_key}"
    else:
        # openai / openai_compat / zhipu / custom relay / LM Studio
        url = f"{base}/models"

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers)
    except Exception as e:  # noqa: BLE001
        return [], f"connection error: {e}"

    if resp.status_code >= 400:
        return [], f"HTTP {resp.status_code}: {resp.text[:200]}"

    try:
        data = resp.json()
    except Exception as e:  # noqa: BLE001
        return [], f"non-JSON response: {e}"

    models: list[dict[str, Any]] = []
    if spec.id == "google" or (spec.kind == "google" and spec.id != "google"):
        # Gemini (built-in or custom): { "models": [{ "name": "models/...", "displayName": "..." }] }
        for m in data.get("models", []):
            name = m.get("name", "")
            models.append({
                "id": name.removeprefix("models/"),
                "display_name": m.get("displayName") or name.removeprefix("models/"),
            })
    elif spec.id == "ollama":
        # Ollama: { "models": [{ "name": "llama3.3:latest", ... }] }
        for m in data.get("models", []):
            name = m.get("name", "")
            models.append({"id": name, "display_name": name})
    else:
        # OpenAI-compat / Anthropic / custom relay: { "data": [{ "id": "...", "display_name": "..." }] }
        for m in data.get("data", []):
            mid = m.get("id", "")
            models.append({
                "id": mid,
                "display_name": m.get("display_name") or mid,
            })

    return models, None


@router.get("/{provider_id}/models")
async def list_provider_models(provider_id: str) -> dict[str, Any]:
    """Pull the live model catalog from the provider's API.

    This is *not* the same as the preset's `default_models` list (which
    is a hard-coded snapshot of well-known models). This endpoint
    queries the provider's own `/models` (or equivalent) endpoint, so
    the user can pick up newly-released models before we ship an
    update to the preset catalog.

    Works for both built-in presets and user-defined custom providers
    (relay stations / private gateways).
    """
    m = _m()

    # Resolve a duck-typed spec (id/kind/base_url) for either a preset
    # or a custom provider.
    preset = get_preset(provider_id)
    if preset is not None:
        spec: Any = preset
        is_local = preset.is_local
        api_key_env = preset.api_key_env
    elif m.is_custom(provider_id):
        cfg = m._custom[provider_id]  # noqa: SLF001  (intentional: read-only view)
        # Lightweight namespace so `_fetch_live_models` can treat it
        # like a preset without us duplicating dispatch logic.
        from types import SimpleNamespace

        spec = SimpleNamespace(
            id=provider_id,
            kind=str(cfg["kind"]),
            base_url=str(cfg["base_url"]),
        )
        is_local = False
        api_key_env = str(cfg["api_key_env"])
    else:
        raise HTTPException(status_code=404, detail="unknown provider")

    if not spec.base_url:
        raise HTTPException(status_code=400, detail="provider has no base_url")
    api_key = os.environ.get(api_key_env, "") if api_key_env else ""
    if not api_key and not is_local:
        raise HTTPException(
            status_code=400,
            detail=f"env var {api_key_env!r} is empty; add the key first",
        )
    models, err = _fetch_live_models(spec, api_key)
    if err is not None:
        return {"ok": False, "error": err, "models": []}
    return {"ok": True, "models": models, "count": len(models)}
