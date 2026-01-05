import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

interface AppState {
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  // Theme could also be managed here or via a dedicated store,
  // currently we are just demonstrating the pattern.
}

export const useAppStore = create<AppState>()(
  immer((set) => ({
    isSidebarOpen: true,
    toggleSidebar: () =>
      set((state) => {
        state.isSidebarOpen = !state.isSidebarOpen;
      }),
  })),
);
