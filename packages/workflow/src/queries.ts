import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { WorkflowClient } from './client.js';
import type { Task, Workflow } from './types.js';

const client = new WorkflowClient();

/** Query: one workflow by id. */
export function useWorkflow(id: string | null): UseQueryResult<Workflow | null> {
  return useQuery({
    queryKey: ['workflow', id],
    queryFn: () => (id === null ? Promise.resolve(null) : client.getWorkflow(id)),
    enabled: id !== null,
    refetchInterval: 2_000,
  });
}

/** Query: workflows list (most recent N). */
export function useWorkflows(limit = 50): UseQueryResult<Workflow[]> {
  return useQuery({
    queryKey: ['workflows', limit],
    queryFn: () => client.listWorkflows(limit),
    refetchInterval: 5_000,
  });
}

/** Query: tasks for a workflow. */
export function useTasks(workflowId: string | null): UseQueryResult<Task[]> {
  return useQuery({
    queryKey: ['tasks', workflowId],
    queryFn: () => (workflowId === null ? Promise.resolve([]) : client.listTasks(workflowId)),
    enabled: workflowId !== null,
    refetchInterval: 2_000,
  });
}
