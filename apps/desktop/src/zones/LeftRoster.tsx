import { AgentCard } from '@aco/ui';

/**
 * Z2 — left roster. Lists every agent with status.
 * See `docs/UI_GUIDELINES.md` §3 Z2.
 */
export function LeftRoster() {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="px-1 text-xs font-semibold uppercase tracking-wide text-text-secondary">
        Chief
      </h2>
      <AgentCard
        role="chief"
        name="Chief"
        status="thinking"
        subtitle="Calm strategist"
        progress={0.42}
      />

      <h2 className="mt-3 px-1 text-xs font-semibold uppercase tracking-wide text-text-secondary">
        Critics
      </h2>
      <AgentCard role="critic-a" name="Critic A" status="idle" subtitle="Bug hunter" />
      <AgentCard role="critic-b" name="Critic B" status="idle" subtitle="Architect" />

      <h2 className="mt-3 px-1 text-xs font-semibold uppercase tracking-wide text-text-secondary">
        Workers
      </h2>
      <AgentCard
        role="worker"
        name="Backend · login"
        status="queued"
        subtitle="Waiting on plan"
      />
    </div>
  );
}
