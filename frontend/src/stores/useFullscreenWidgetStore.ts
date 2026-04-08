import { create } from "zustand";

interface FullscreenWidgetState {
  fullscreenInstanceId: string | null;
  openFullscreen: (instanceId: string) => void;
  closeFullscreen: () => void;
}

export const useFullscreenWidgetStore = create<FullscreenWidgetState>()(
  (set) => ({
    fullscreenInstanceId: null,
    openFullscreen: (instanceId: string) =>
      set({ fullscreenInstanceId: instanceId }),
    closeFullscreen: () => set({ fullscreenInstanceId: null }),
  }),
);
