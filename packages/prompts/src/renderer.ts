/**
 * Minimal prompt template renderer.
 *
 * Supports `{{ var.path }}` substitution with strict, deterministic
 * semantics. **No** `eval`, **no** arbitrary expressions. Variables
 * must be present in the context; missing variables throw.
 *
 * Mirrors the Python renderer in `runtime/prompts/renderer.py`. The
 * two implementations are kept in sync manually; CI runs a fixture
 * diff to catch drift.
 */

export class PromptRenderError extends Error {
  constructor(
    message: string,
    public readonly path: string,
  ) {
    super(`${path}: ${message}`);
    this.name = 'PromptRenderError';
  }
}

const VAR_PATTERN = /\{\{\s*([a-zA-Z_][\w.]*)\s*\}\}/g;

export type Context = Readonly<Record<string, unknown>>;

function lookup(ctx: Context, path: string): string {
  const parts = path.split('.');
  let cur: unknown = ctx;
  for (const p of parts) {
    if (cur === null || cur === undefined || typeof cur !== 'object') {
      throw new PromptRenderError(`cannot read "${p}" of non-object`, path);
    }
    cur = (cur as Record<string, unknown>)[p];
    if (cur === undefined) {
      throw new PromptRenderError(`undefined variable`, path);
    }
  }
  if (cur === null) return 'null';
  if (typeof cur === 'string') return cur;
  if (typeof cur === 'number' || typeof cur === 'boolean') return String(cur);
  throw new PromptRenderError(`unsupported type: ${typeof cur}`, path);
}

export function render(template: string, ctx: Context): string {
  return template.replace(VAR_PATTERN, (_match, path: string) => lookup(ctx, path));
}

/** Estimate token count (very rough: 4 chars ≈ 1 token). */
export function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}
