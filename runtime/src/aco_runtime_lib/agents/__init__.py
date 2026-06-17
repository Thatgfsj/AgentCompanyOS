"""Agent implementations: Chief, Critic A/B, Worker, Planner, Merger, Reporter.

Phase 0 ships the ABCs only; real LLM calls land in Phase 1.
See `docs/PROMPT_GUIDE.md` and `prompts/*.md` for the prompts.
"""

from aco_runtime_lib.agents.base import Agent, AgentRole

__all__ = ["Agent", "AgentRole"]
