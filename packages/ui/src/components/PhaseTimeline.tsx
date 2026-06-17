import { cn } from '../lib/cn.js';

export type PhaseName =
  | 'requirement'
  | 'planning'
  | 'plan_review'
  | 'dispatch'
  | 'development'
  | 'review'
  | 'repair'
  | 'delivery';

export type PhaseState = 'pending' | 'active' | 'done' | 'failed';

export interface PhaseStep {
  name: PhaseName;
  state: PhaseState;
  label: string;
  durationMs?: number;
}

export interface PhaseTimelineProps {
  steps: readonly PhaseStep[];
  onStepClick?: (name: PhaseName) => void;
  className?: string;
}

const stateColor: Record<PhaseState, string> = {
  pending: 'bg-status-pending/40 text-text-secondary',
  active: 'bg-status-active text-white animate-pulse',
  done: 'bg-status-done text-white',
  failed: 'bg-status-failed text-white',
};

/**
 * Horizontal 8-step stepper. See `docs/UI_GUIDELINES.md` §3 T0.
 */
export function PhaseTimeline({ steps, onStepClick, className }: PhaseTimelineProps) {
  return (
    <ol
      className={cn('flex w-full items-center gap-1 overflow-x-auto p-2', className)}
      aria-label="Workflow phase timeline"
    >
      {steps.map((s, i) => (
        <li key={s.name} className="flex-1 min-w-[100px]">
          <button
            type="button"
            onClick={() => onStepClick?.(s.name)}
            className={cn(
              'flex w-full flex-col items-center gap-1 rounded-md p-2 text-xs transition-colors',
              'hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-chief',
            )}
            aria-label={`${s.label} (${s.state})`}
          >
            <span
              className={cn(
                'flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold',
                stateColor[s.state],
              )}
            >
              {i + 1}
            </span>
            <span className="truncate text-center">{s.label}</span>
            {s.durationMs !== undefined && (
              <span className="text-[10px] text-text-secondary">
                {Math.round(s.durationMs / 1000)}s
              </span>
            )}
          </button>
        </li>
      ))}
    </ol>
  );
}
