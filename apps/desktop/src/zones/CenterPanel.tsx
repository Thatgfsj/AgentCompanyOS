import type { ReactNode } from 'react';
import { Card, ReasoningBubble, ReviewVerdict } from '@aco/ui';

export interface CenterPanelProps {
  chiefCard: ReactNode;
}

/**
 * Z3 — center panel. Current reasoning / review / task.
 * See `docs/UI_GUIDELINES.md` §3 Z3.
 */
export function CenterPanel({ chiefCard }: CenterPanelProps) {
  return (
    <div className="flex flex-col gap-3">
      {chiefCard}

      <ReasoningBubble
        agentName="Chief Agent"
        roleColorClass="border-t-chief"
        step="Planning — drafting API"
        body="Drafting a plan with 4 tasks: backend /login, frontend LoginForm, database users table, and tests. Estimated 9k input tokens, 4k output."
        ago="2s ago"
      />

      <Card>
        <h3 className="mb-2 text-sm font-semibold">Critic B — Architect review</h3>
        <ReviewVerdict
          verdict="PASS"
          confidence={0.87}
          issues={[]}
          summary="Boundaries are clean. Auth module is decoupled from the route handler. Good."
        />
      </Card>
    </div>
  );
}
