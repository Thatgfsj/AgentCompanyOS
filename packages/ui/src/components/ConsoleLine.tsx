import { cn } from '../lib/cn.js';

export type ConsoleSource = 'chief' | 'worker' | 'critic-a' | 'critic-b' | 'system';

export interface ConsoleLineProps {
  ts: string;
  source: ConsoleSource;
  text: string;
  className?: string;
}

const sourceColor: Record<ConsoleSource, string> = {
  chief: 'text-chief',
  worker: 'text-worker-1',
  'critic-a': 'text-critic-a',
  'critic-b': 'text-critic-b',
  system: 'text-text-secondary',
};

/**
 * A single line in the bottom console. See `docs/UI_GUIDELINES.md` §6.6.
 */
export function ConsoleLine({ ts, source, text, className }: ConsoleLineProps) {
  return (
    <div
      className={cn(
        'flex gap-2 font-mono text-[13px] leading-snug',
        sourceColor[source],
        className,
      )}
    >
      <span className="shrink-0 text-text-secondary tabular-nums">[{ts}]</span>
      <span className="shrink-0 uppercase tracking-wide">{source}</span>
      <span className="min-w-0 flex-1 truncate text-primary">{text}</span>
    </div>
  );
}
