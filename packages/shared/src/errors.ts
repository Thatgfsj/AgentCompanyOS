/**
 * Typed error codes for the agent protocol and the runtime.
 *
 * See `docs/AGENT_PROTOCOL.md` §7 (isolation) and §11 (error handling).
 */

export type ErrorCode =
  // Generic
  | 'parse_error'
  | 'invalid_request'
  | 'method_not_found'
  | 'invalid_params'
  | 'internal_error'
  // Auth
  | 'auth_missing'
  | 'auth_invalid'
  | 'auth_denied'
  // Workflow
  | 'workflow_not_found'
  | 'workflow_aborted'
  | 'workflow_budget_exceeded'
  | 'workflow_invalid_transition'
  // Provider
  | 'provider_unavailable'
  | 'provider_rate_limited'
  | 'provider_context_exceeded'
  | 'provider_content_filtered'
  // Plugin
  | 'plugin_not_found'
  | 'plugin_load_failed'
  | 'plugin_capability_denied'
  // Storage
  | 'storage_corrupt'
  | 'storage_disk_full'
  | 'storage_locked';

export interface AcoError {
  readonly code: ErrorCode;
  readonly message: string;
  /** Additional context (paths, ids, etc.). */
  readonly data?: Readonly<Record<string, unknown>>;
  /** Stack trace if available. */
  readonly stack?: string;
}

export function makeError(
  code: ErrorCode,
  message: string,
  data?: Readonly<Record<string, unknown>>,
): AcoError {
  return data === undefined ? { code, message } : { code, message, data };
}
