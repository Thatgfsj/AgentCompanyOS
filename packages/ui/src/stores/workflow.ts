import { create } from 'zustand';
import type { WfEvent } from '@aco/shared';

interface WorkflowState {
  currentWfId: string | null;
  recentEvents: WfEvent[];
  selectedTaskId: string | null;
  setCurrentWorkflow: (id: string | null) => void;
  appendEvent: (event: WfEvent) => void;
  selectTask: (id: string | null) => void;
  clearEvents: () => void;
}

const MAX_RECENT = 500;

/**
 * Workflow-level state: which workflow is active, the last N events,
 * and the currently focused task. The event log is bounded.
 */
export const useWorkflowStore = create<WorkflowState>((set) => ({
  currentWfId: null,
  recentEvents: [],
  selectedTaskId: null,
  setCurrentWorkflow: (id) => {
    set({ currentWfId: id, recentEvents: [], selectedTaskId: null });
  },
  appendEvent: (event) => {
    set((s) => {
      const next = [...s.recentEvents, event];
      if (next.length > MAX_RECENT) next.splice(0, next.length - MAX_RECENT);
      return { recentEvents: next };
    });
  },
  selectTask: (id) => {
    set({ selectedTaskId: id });
  },
  clearEvents: () => {
    set({ recentEvents: [] });
  },
}));
