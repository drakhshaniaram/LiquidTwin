import { create } from 'zustand';

type WorkspaceState = {
  activeTerminalId: string | null;
  setActiveTerminal: (terminalId: string | null) => void;
};

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  activeTerminalId:
    typeof localStorage === 'undefined' ? null : localStorage.getItem('activeTerminalId'),
  setActiveTerminal: (terminalId) => {
    if (typeof localStorage !== 'undefined') {
      if (terminalId) localStorage.setItem('activeTerminalId', terminalId);
      else localStorage.removeItem('activeTerminalId');
    }
    set({ activeTerminalId: terminalId });
  },
}));
