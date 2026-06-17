import { useState } from 'react';
import { PhaseTimeline, AgentCard, Card, Button, type PhaseState } from '@aco/ui';
import type { WfEvent } from '@aco/shared';
import { TopBar } from './zones/TopBar.js';
import { LeftRoster } from './zones/LeftRoster.js';
import { CenterPanel } from './zones/CenterPanel.js';
import { RightPanel } from './zones/RightPanel.js';
import { BottomConsole } from './zones/BottomConsole.js';

const PHASES: ReadonlyArray<{ name: 'requirement' | 'planning' | 'plan_review' | 'dispatch' | 'development' | 'review' | 'repair' | 'delivery'; label: string }> = [
  { name: 'requirement', label: 'Requirement' },
  { name: 'planning', label: 'Planning' },
  { name: 'plan_review', label: 'Plan Review' },
  { name: 'dispatch', label: 'Dispatch' },
  { name: 'development', label: 'Development' },
  { name: 'review', label: 'Review' },
  { name: 'repair', label: 'Repair' },
  { name: 'delivery', label: 'Delivery' },
];

function phaseState(active: number, current: number): PhaseState {
  if (current < active) return 'done';
  if (current === active) return 'active';
  return 'pending';
}

export function App() {
  const [activePhase, setActivePhase] = useState(0);
  const [events, setEvents] = useState<WfEvent[]>([]);
  const [cmd, setCmd] = useState('');

  const handleSubmit = () => {
    if (cmd.trim().length === 0) return;
    setEvents((prev) => [
      ...prev,
      { kind: 'console', agent_id: 'agent:user', level: 'info', message: `> ${cmd}` },
    ]);
    setCmd('');
  };

  return (
    <div className="flex h-screen flex-col">
      <TopBar
        commandInput={cmd}
        onCommandChange={setCmd}
        onCommandSubmit={handleSubmit}
        projectName="Agent Company OS"
      />

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-[280px] shrink-0 border-r border-border bg-surface-2 p-2 overflow-y-auto">
          <LeftRoster />
        </aside>

        <main className="flex-1 overflow-y-auto p-3">
          <Card className="mb-3">
            <PhaseTimeline
              steps={PHASES.map((p, i) => ({
                name: p.name,
                label: p.label,
                state: phaseState(i, activePhase),
              }))}
              onStepClick={(name) => {
                const idx = PHASES.findIndex((p) => p.name === name);
                if (idx >= 0) setActivePhase(idx);
              }}
            />
          </Card>

          <CenterPanel
            chiefCard={
              <AgentCard
                role="chief"
                name="Chief Agent"
                status="thinking"
                subtitle="Calm strategist · analyzing"
                progress={0.42}
              />
            }
          />
        </main>

        <aside className="w-[360px] shrink-0 border-l border-border bg-surface-2 p-3 overflow-y-auto">
          <RightPanel />
        </aside>
      </div>

      <BottomConsole events={events} />

      <div className="hidden">
        <Button variant="primary">stub</Button>
      </div>
    </div>
  );
}
