"""Critic A and Critic B agents.

Each is a thin wrapper that:
1. Receives the deliverable (file contents or summary) + criteria.
2. Sends to the provider with its role-specific system prompt.
3. Parses the JSON verdict.

See `prompts/critic_a.md` and `prompts/critic_b.md`.
"""

from __future__ import annotations

from typing import Any

from aco_runtime_lib.agents._json_extract import extract_all_json_objects
from aco_runtime_lib.agents.base import Agent, AgentResult, AgentRole
from aco_runtime_lib.event_bus import EventBus
from aco_runtime_lib.providers.base import ChatMessage, ChatRequest, ProviderError
from aco_runtime_lib.providers.router import ModelRouter


class CriticAgent(Agent):
    """A Critic (A or B). The role determines which system prompt and
    which router role key is used.
    """

    def __init__(
        self,
        role: AgentRole,
        router: ModelRouter,
        bus: EventBus,
        router_role: str,
        system_prompt: str,
    ) -> None:
        if role not in (AgentRole.CRITIC_A, AgentRole.CRITIC_B):
            raise ValueError(f"CriticAgent must be CRITIC_A or CRITIC_B, got {role}")
        self.role = role
        self._router = router
        self._bus = bus
        self._router_role = router_role
        self._system_prompt = system_prompt

    async def run(self, ctx: dict[str, Any]) -> AgentResult:
        provider, ref = self._router.pick(self._router_role)
        subject = ctx.get("subject", "")
        ask = ctx.get("ask", "")
        files = ctx.get("files", [])
        request = ChatRequest(
            model=ref.model_id,
            messages=[
                ChatMessage(role="system", content=self._system_prompt),
                ChatMessage(
                    role="user",
                    content=(
                        f"## Subject\n{subject}\n\n"
                        f"## Ask\n{ask}\n\n"
                        f"## Files\n" + "\n".join(f"- {f}" for f in files)
                    ),
                ),
            ],
            max_tokens=2048,
            temperature=0.2,
        )
        try:
            response = await provider.chat(request)
        except ProviderError as e:
            return AgentResult(
                role=self.role,
                data={"error": "provider_error", "message": str(e), "retryable": e.retryable},
            )
        verdict = _parse_verdict(response.content)
        return AgentResult(
            role=self.role,
            data={
                "verdict": verdict.get("verdict", "PASS"),
                "confidence": verdict.get("confidence", 1.0),
                "issues": verdict.get("issues", []),
                "summary": verdict.get("summary", ""),
                "raw": response.content,
            },
        )


def _parse_verdict(text: str) -> dict[str, Any]:
    """Find the last JSON object in `text` that has a `verdict` field.

    On parse failure, returns a `REPAIR` verdict with confidence 0.0 and a
    synthetic `parse_failure` issue — **never** silently PASSes. The previous
    default (verdict=PASS, confidence=1.0, issues=[]) caused the
    v0.2.1 validate_minimax false negative: the model's analysis was
    present in `summary` but its JSON verdict object got truncated by
    max_tokens=512, so `_parse_verdict` found no verdict and quietly
    accepted the code as PASS.
    """
    objs = extract_all_json_objects(text)
    for obj in reversed(objs):
        if "verdict" in obj:
            return obj
    return {
        "verdict": "REPAIR",
        "confidence": 0.0,
        "issues": [
            {
                "severity": "MAJOR",
                "kind": "parse_failure",
                "description": (
                    "Critic did not emit a REVIEW_RESPONSE JSON object with a "
                    "'verdict' field. The raw response was captured in 'summary' "
                    "for triage; treat as REPAIR until the model is fixed to emit "
                    "structured output."
                ),
            }
        ],
        "summary": text,
    }
