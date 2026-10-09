import { create } from 'zustand';

type FocusedRoute = {
  terminalId: string;
  elementIds: string[];
};

type WorkspaceState = {
  activeTerminalId: string | null;
  focusedRoute: FocusedRoute | null;
  setActiveTerminal: (terminalId: string | null) => void;
  setFocusedRoute: (route: FocusedRoute | null) => void;
};

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  activeTerminalId:
    typeof localStorage === 'undefined' ? null : localStorage.getItem('activeTerminalId'),
  focusedRoute: null,
  setActiveTerminal: (terminalId) => {
    if (typeof localStorage !== 'undefined') {
      if (terminalId) localStorage.setItem('activeTerminalId', terminalId);
      else localStorage.removeItem('activeTerminalId');
    }
    set({ activeTerminalId: terminalId });
  },
  setFocusedRoute: (route) => set({ focusedRoute: route }),
}));
