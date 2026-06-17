/**
 * Agent protocol envelope and message types.
 *
 * Mirror of `docs/AGENT_PROTOCOL.md` §3-§5.
 * Versioned as `agent-protocol/v0.1`.
 */

export const AGENT_PROTOCOL_VERSION = 'agent-protocol/v0.1' as const;

export type AgentId =
  | 'agent:chief'
  | 'agent:critic:a'
  | 'agent:critic:b'
  | 'agent:user'
  | `agent:worker:${string}`
  | 'agent:reporter';

export interface Envelope<T extends MessageType, P> {
  /** ULID. */
  readonly id: string;
  readonly schema: typeof AGENT_PROTOCOL_VERSION;
  readonly from: AgentId;
  readonly to: AgentId;
  readonly type: T;
  /** ISO 8601 timestamp. */
  readonly ts: string;
  /** workflow + phase correlation. */
  readonly trace: string;
  readonly payload: P;
}

export type MessageType =
  | 'TASK_ASSIGN'
  | 'TASK_PROGRESS'
  | 'TASK_RESULT'
  | 'TASK_QUESTION'
  | 'REVIEW_REQUEST'
  | 'REVIEW_RESPONSE'
  | 'REPAIR_REQUEST'
  | 'DISPATCH_PLAN'
  | 'ESCALATE'
  | 'USER_QUERY'
  | 'USER_RESPONSE'
  | 'USER_FEEDBACK'
  | 'ABORT'
  | 'SHUTDOWN';

// ─── Payloads ──────────────────────────────────────────────────────

export interface TaskAssignPayload {
  readonly task_id: string;
  readonly title: string;
  readonly objective: string;
  readonly interfaces: {
    readonly consumes: readonly string[];
    readonly produces: readonly string[];
  };
  readonly dependencies: readonly string[];
  readonly constraints: readonly string[];
  readonly deliverables: readonly string[];
  readonly context_budget_tokens: number;
  readonly model_hint?: string;
}

export type TaskResultStatus = 'DONE' | 'FAILED' | 'PARTIAL';

export interface TaskResultPayload {
  readonly task_id: string;
  readonly status: TaskResultStatus;
  readonly summary: string;
  readonly files_modified: readonly {
    readonly path: string;
    readonly lines_added: number;
    readonly lines_removed: number;
  }[];
  readonly tests_run?: {
    readonly passed: number;
    readonly failed: number;
    readonly skipped: number;
  };
  readonly artifacts?: readonly string[];
  readonly logs_ref?: string;
}

export type ReviewVerdict = 'PASS' | 'REPAIR' | 'REWRITE';
export type IssueSeverity = 'MAJOR' | 'MINOR' | 'NIT';

export interface ReviewResponsePayload {
  readonly review_id: string;
  readonly verdict: ReviewVerdict;
  readonly confidence: number;
  readonly issues: readonly {
    readonly severity: IssueSeverity;
    readonly file?: string;
    readonly line?: number;
    readonly message: string;
    readonly suggested_fix?: string;
  }[];
  readonly summary: string;
}

export interface UserQueryPayload {
  readonly question: string;
  readonly options: readonly string[];
}

export interface UserResponsePayload {
  readonly answer: string;
  readonly freeform?: string;
}
