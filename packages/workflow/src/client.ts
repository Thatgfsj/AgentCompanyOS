import type { Task, Workflow } from './types.js';

/**
 * Thin client over Tauri IPC for workflow operations.
 *
 * Each method is a thin wrapper over `tauri::invoke`. The matching
 * Rust commands live in `crates/tauri-core/src/lib.rs`.
 */
export class WorkflowClient {
  private readonly invoke: <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;

  constructor(
    invoke: <T>(cmd: string, args?: Record<string, unknown>) => Promise<T> = defaultInvoke,
  ) {
    this.invoke = invoke;
  }

  /** Start a new workflow. Returns the new workflow id. */
  async startWorkflow(text: string, projectId?: string): Promise<string> {
    const result = await this.invoke<{ id: string }>('start_workflow', {
      req: { text, projectId: projectId ?? null },
    });
    return result.id;
  }

  /** Fetch a workflow by id. */
  async getWorkflow(id: string): Promise<Workflow | null> {
    return (await this.invoke<Workflow | null>('get_workflow', { id })) ?? null;
  }

  /** List workflows, most recent first. */
  async listWorkflows(limit = 50): Promise<Workflow[]> {
    return await this.invoke<Workflow[]>('list_workflows', { limit });
  }

  /** Fetch a task by id. */
  async getTask(id: string): Promise<Task | null> {
    return (await this.invoke<Task | null>('get_task', { id })) ?? null;
  }

  /** List tasks for a workflow. */
  async listTasks(workflowId: string): Promise<Task[]> {
    return await this.invoke<Task[]>('list_tasks', { workflowId });
  }

  /** Cancel an in-flight workflow. */
  async cancelWorkflow(id: string): Promise<void> {
    await this.invoke<void>('cancel_workflow', { id });
  }
}

async function defaultInvoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  // Dynamic import to keep this package usable outside Tauri.
  const { invoke } = await import('@tauri-apps/api/core');
  return await invoke<T>(cmd, args);
}
