"""Prompt template loader and renderer.

Mirror of `packages/prompts/src/renderer.ts` (TypeScript) and the
`prompts/*.md` files at the repo root. Phase 0 ships a no-op loader;
Phase 1 reads from disk and renders with strict variable substitution.
"""

from aco_runtime_lib.prompts.renderer import PromptRenderError, estimate_tokens, render

__all__ = ["PromptRenderError", "estimate_tokens", "render"]
