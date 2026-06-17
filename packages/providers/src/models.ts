/**
 * Provider model registry.
 *
 * Mirror of `crates/config/src/lib.rs` `ModelSpec` and
 * `config/providers.toml`. This file is a TypeScript-friendly
 * snapshot used by the UI for capability lookups; the source of
 * truth for runtime config is `providers.toml`.
 *
 * See `docs/PROVIDER_SPEC.md` §4.
 */

export type ProviderId =
  | 'anthropic'
  | 'openai'
  | 'google'
  | 'kimi'
  | 'minimax'
  | 'deepseek'
  | 'siliconflow'
  | 'openrouter'
  | 'ollama'
  | 'lmstudio'
  | 'custom';

export type Capability =
  | 'chat'
  | 'stream'
  | 'vision'
  | 'tool_call'
  | 'parallel_tool_calls'
  | 'json_mode'
  | 'prompt_caching'
  | 'reasoning_effort';

export interface ModelInfo {
  readonly id: string;
  readonly displayName: string;
  readonly contextWindow: number;
  readonly maxOutputTokens: number;
  readonly inputCostPerMtok: number;
  readonly outputCostPerMtok: number;
  readonly capabilities: readonly Capability[];
  readonly deprecated?: boolean;
  readonly sunsetDate?: string;
}

export interface ProviderInfo {
  readonly id: ProviderId;
  readonly displayName: string;
  readonly baseUrl: string;
  readonly apiKeyEnv: string;
  readonly models: readonly ModelInfo[];
}

/**
 * Snapshot of well-known models. The actual runtime config is loaded
 * from `providers.toml`; this table is for UI hints and offline dev.
 */
export const KNOWN_MODELS: readonly ProviderInfo[] = [
  {
    id: 'anthropic',
    displayName: 'Anthropic',
    baseUrl: 'https://api.anthropic.com',
    apiKeyEnv: 'ANTHROPIC_API_KEY',
    models: [
      {
        id: 'claude-opus-4-8',
        displayName: 'Claude Opus 4.8',
        contextWindow: 200_000,
        maxOutputTokens: 32_000,
        inputCostPerMtok: 15.0,
        outputCostPerMtok: 75.0,
        capabilities: [
          'chat',
          'stream',
          'vision',
          'tool_call',
          'json_mode',
          'prompt_caching',
          'reasoning_effort',
        ],
      },
      {
        id: 'claude-sonnet-4-6',
        displayName: 'Claude Sonnet 4.6',
        contextWindow: 200_000,
        maxOutputTokens: 16_000,
        inputCostPerMtok: 3.0,
        outputCostPerMtok: 15.0,
        capabilities: [
          'chat',
          'stream',
          'vision',
          'tool_call',
          'json_mode',
          'prompt_caching',
          'reasoning_effort',
        ],
      },
    ],
  },
  {
    id: 'openai',
    displayName: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    apiKeyEnv: 'OPENAI_API_KEY',
    models: [
      {
        id: 'gpt-5',
        displayName: 'GPT-5',
        contextWindow: 128_000,
        maxOutputTokens: 16_000,
        inputCostPerMtok: 5.0,
        outputCostPerMtok: 20.0,
        capabilities: ['chat', 'stream', 'vision', 'tool_call', 'json_mode'],
      },
    ],
  },
  {
    id: 'google',
    displayName: 'Google Gemini',
    baseUrl: 'https://generativelanguage.googleapis.com',
    apiKeyEnv: 'GOOGLE_API_KEY',
    models: [
      {
        id: 'gemini-2-5-pro',
        displayName: 'Gemini 2.5 Pro',
        contextWindow: 1_000_000,
        maxOutputTokens: 8_000,
        inputCostPerMtok: 2.5,
        outputCostPerMtok: 10.0,
        capabilities: ['chat', 'stream', 'vision', 'tool_call', 'json_mode'],
      },
    ],
  },
  {
    id: 'minimax',
    displayName: 'MiniMax',
    baseUrl: 'https://api.minimaxi.com/v1',
    apiKeyEnv: 'MINIMAX_API_KEY',
    models: [
      {
        id: 'minimax-m3',
        displayName: 'MiniMax M3',
        contextWindow: 32_000,
        maxOutputTokens: 8_000,
        inputCostPerMtok: 0.5,
        outputCostPerMtok: 1.0,
        capabilities: ['chat', 'stream', 'json_mode'],
      },
    ],
  },
  {
    id: 'kimi',
    displayName: 'Moonshot (Kimi)',
    baseUrl: 'https://api.moonshot.cn/v1',
    apiKeyEnv: 'MOONSHOT_API_KEY',
    models: [
      {
        id: 'kimi-k2',
        displayName: 'Kimi K2',
        contextWindow: 128_000,
        maxOutputTokens: 8_000,
        inputCostPerMtok: 1.0,
        outputCostPerMtok: 3.0,
        capabilities: ['chat', 'stream', 'tool_call', 'json_mode'],
      },
    ],
  },
];

/** Find a model by `provider:model` string. */
export function findModel(reference: string): { provider: ProviderInfo; model: ModelInfo } | null {
  const idx = reference.indexOf(':');
  if (idx <= 0) return null;
  const providerId = reference.slice(0, idx) as ProviderId;
  const modelId = reference.slice(idx + 1);
  const provider = KNOWN_MODELS.find((p) => p.id === providerId);
  if (!provider) return null;
  const model = provider.models.find((m) => m.id === modelId);
  if (!model) return null;
  return { provider, model };
}
