import { create } from 'zustand';

export type ZoneId = 'left' | 'center' | 'right' | 'bottom';

interface UiState {
  activeZone: ZoneId;
  consoleVisible: boolean;
  consoleHeightPx: number;
  setActiveZone: (zone: ZoneId) => void;
  toggleConsole: () => void;
  setConsoleHeight: (px: number) => void;
}

/**
 * UI-only state (which zone is focused, console visibility, etc.).
 * Workflow state lives in `workflow.js`; server state in TanStack Query.
 */
export const useUiStore = create<UiState>((set) => ({
  activeZone: 'center',
  consoleVisible: true,
  consoleHeightPx: 240,
  setActiveZone: (zone) => {
    set({ activeZone: zone });
  },
  toggleConsole: () => {
    set((s) => ({ consoleVisible: !s.consoleVisible }));
  },
  setConsoleHeight: (px) => {
    set({ consoleHeightPx: Math.max(80, Math.min(800, px)) });
  },
}));
