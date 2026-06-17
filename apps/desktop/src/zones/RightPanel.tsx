import { Card, TaskItem } from '@aco/ui';

/**
 * Z4 — right panel. Task list, progress, current file.
 * See `docs/UI_GUIDELINES.md` §3 Z4.
 */
export function RightPanel() {
  return (
    <div className="flex flex-col gap-3">
      <Card>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold">Tasks</h2>
          <span className="text-xs text-text-secondary">1/4 done</span>
        </div>
        <div className="mb-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
          <div className="h-full bg-status-done" style={{ width: '25%' }} />
        </div>
        <div className="flex flex-col gap-1.5">
          <TaskItem
            title="Backend: implement /login"
            state="DONE"
            owner="Worker 1"
            durationMs={192_000}
            fileHint="src/auth/login.py"
          />
          <TaskItem
            title="Frontend: LoginForm"
            state="IN_PROGRESS"
            owner="Worker 2"
            fileHint="src/components/LoginForm.tsx"
          />
          <TaskItem title="DB: users table" state="PENDING" owner="Worker 3" />
          <TaskItem title="Tests: login flow" state="PENDING" owner="Worker 4" />
        </div>
      </Card>

      <Card>
        <h2 className="mb-2 text-sm font-semibold">Current file</h2>
        <code className="block truncate font-mono text-xs text-text-secondary">
          src/components/LoginForm.tsx
        </code>
        <pre className="mt-2 max-h-32 overflow-y-auto rounded-md bg-surface-2 p-2 font-mono text-xs">
{`export function LoginForm() {
  return (
    <form>
      <input name="email" />
      <input name="password" type="password" />
      <button>Sign in</button>
    </form>
  );
}`}
        </pre>
      </Card>
    </div>
  );
}
