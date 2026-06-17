/**
 * Client-side workflow types. Mirror of the Rust `storage::Workflow`
 * and the Python `runtime/api/schemas.py Workflow` (codegen'd from
 * `packages/shared/schemas/workflow.schema.json` in Phase 1).
 */

export type WorkflowState =
  | 'REQ_RECEIVED'
  | 'REQ_ANALYZING'
  | 'REQ_AWAIT_USER'
  | 'REQ_CLARIFIED'
  | 'PLAN_DRAFTING'
  | 'PLAN_DRAFTED'
  | 'PLAN_UNDER_REVIEW'
  | 'PLAN_REVISING'
  | 'PLAN_APPROVED'
  | 'DISPATCHING'
  | 'DEVELOPING'
  | 'AWAITING_WORKERS'
  | 'REVIEWING'
  | 'REPAIRING'
  | 'REWRITING'
  | 'DELIVERING'
  | 'DONE'
  | 'FAILED'
  | 'ABORTED';

export type WorkflowPhase =
  | '1-requirement'
  | '2-planning'
  | '3-plan-review'
  | '4-dispatch'
  | '5-development'
  | '6-review'
  | '7-repair'
  | '8-delivery';

export type WorkflowFinalStatus = 'DONE' | 'FAILED' | 'ABORTED';

export interface Workflow {
  id: string;
  createdAt: number;
  updatedAt: number;
  state: WorkflowState;
  phase: WorkflowPhase;
  userRequest: string;
  planDoc: string | null;
  summary: string | null;
  finalStatus: WorkflowFinalStatus | null;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalCostUsd: number | null;
}

export type TaskState =
  | 'PENDING'
  | 'DISPATCHED'
  | 'IN_PROGRESS'
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'APPROVED'
  | 'REPAIR_REQUESTED'
  | 'REPAIRING'
  | 'REJECTED'
  | 'DONE'
  | 'FAILED'
  | 'ABORTED';

export interface Task {
  id: string;
  workflowId: string;
  parentId: string | null;
  title: string;
  state: TaskState;
  assignedTo: string | null;
  model: string | null;
  repairCount: number;
  inputTokens: number;
  outputTokens: number;
  costUsd: number | null;
  filesModified: string[];
  startedAt: number | null;
  finishedAt: number | null;
}
