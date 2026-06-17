import { ConsoleLine, type ConsoleSource } from '@aco/ui';
import type { WfEvent, LogLevel } from '@aco/shared';

export interface BottomConsoleProps {
  events: readonly WfEvent[];
}

function agentToSource(agentId: string): ConsoleSource {
  if (agentId === 'agent:chief') return 'chief';
  if (agentId === 'agent:critic:a') return 'critic-a';
  if (agentId === 'agent:critic:b') return 'critic-b';
  if (agentId.startsWith('agent:worker:')) return 'worker';
  return 'system';
}

function shortTime(iso: string): string {
  // ISO -> HH:MM:SS
  return iso.slice(11, 19);
}

function levelChar(level: LogLevel): string {
  switch (level) {
    case 'error': return 'E';
    case 'warn':  return 'W';
    case 'info':  return 'I';
    case 'debug': return 'D';
    case 'trace': return 'T';
  }
}

export function BottomConsole({ events }: BottomConsoleProps) {
  // Show last 200 events; the rest are available in the workflow log.
  const visible = events.slice(-200);
  return (
    <section
      className="h-60 shrink-0 overflow-y-auto border-t border-border bg-surface-2 p-2 font-mono text-[13px]"
      aria-label="Console"
    >
      {visible.length === 0 ? (
        <div className="p-2 text-text-secondary">Console idle.</div>
      ) : (
        <ol className="flex flex-col gap-0.5">
          {visible.map((e, i) => {
            if (e.kind !== 'console') return null;
            return (
              <li key={i}>
                <ConsoleLine
                  ts={shortTime(e.ts)}
                  source={agentToSource(e.agent_id)}
                  text={`[${levelChar(e.level)}] ${e.message}`}
                />
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
