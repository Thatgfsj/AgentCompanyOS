import { AgentCard, type AgentStatus } from '@flowntier/ui';

export interface LeftRosterProps {
  chiefStatus: AgentStatus;
  criticAStatus: AgentStatus;
  criticBStatus: AgentStatus;
  workerStatus: AgentStatus;
}

/**
 * Z2 — left roster. Lists every agent with status.
 */
export function LeftRoster({
  chiefStatus,
  criticAStatus,
  criticBStatus,
  workerStatus,
}: LeftRosterProps) {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="px-1 text-xs font-semibold uppercase tracking-wide text-text-secondary">
        主理
      </h2>
      <AgentCard
        role="chief"
        name="主理代理"
        status={chiefStatus}
        subtitle="沉稳的策略师 · 正在分析"
        progress={chiefStatus === 'thinking' ? 0.5 : undefined}
      />

      <h2 className="mt-3 px-1 text-xs font-semibold uppercase tracking-wide text-text-secondary">
        审核员
      </h2>
      <AgentCard
        role="critic-a"
        name="审核员 A"
        status={criticAStatus}
        subtitle="找茬"
      />
      <AgentCard
        role="critic-b"
        name="审核员 B"
        status={criticBStatus}
        subtitle="架构师"
      />

      <h2 className="mt-3 px-1 text-xs font-semibold uppercase tracking-wide text-text-secondary">
        实施
      </h2>
      <AgentCard
        role="worker"
        name="实施"
        status={workerStatus}
        subtitle="执行任务中"
      />
    </div>
  );
}
