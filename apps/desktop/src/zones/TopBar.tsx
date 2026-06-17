import type { FormEvent } from 'react';

export interface TopBarProps {
  commandInput: string;
  onCommandChange: (value: string) => void;
  onCommandSubmit: () => void;
  projectName: string;
}

/**
 * Z1 — top bar. Command input + project name + user menu.
 * See `docs/UI_GUIDELINES.md` §3 Z1.
 */
export function TopBar({ commandInput, onCommandChange, onCommandSubmit, projectName }: TopBarProps) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onCommandSubmit();
  };

  return (
    <header className="flex h-16 shrink-0 items-center gap-4 border-b border-border bg-surface-2 px-4">
      <div className="font-semibold tracking-tight">{projectName}</div>
      <form onSubmit={handleSubmit} className="flex-1">
        <input
          type="text"
          value={commandInput}
          onChange={(e) => onCommandChange(e.target.value)}
          placeholder="Ask the Chief…  (e.g. 'Add a /login endpoint')"
          className="w-full rounded-md border border-border bg-surface-1 px-3 py-2 text-sm placeholder:text-text-secondary focus:border-chief focus:outline-none focus:ring-2 focus:ring-chief/50"
          aria-label="Command input"
        />
      </form>
      <button
        type="button"
        className="rounded-md border border-border bg-surface-1 px-3 py-1.5 text-xs text-text-secondary hover:text-primary focus:outline-none focus:ring-2 focus:ring-chief/50"
      >
        Settings
      </button>
    </header>
  );
}
