import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

import api from "@/api";

interface UserPreferencesState {
  themeMode: "light" | "dark";
  setThemeMode: (mode: "light" | "dark") => void;
  toggleTheme: () => void;
  fetchPreferences: () => Promise<void>;
}

export const useUserPreferencesStore = create<UserPreferencesState>()(
  immer((set, get) => ({
    themeMode: "light",
    setThemeMode: async (mode) => {
      set((state) => {
        state.themeMode = mode;
      });
      try {
        await api.put("/api/v1/users/me/preferences", { theme: mode });
      } catch (error) {
        console.error("Failed to save preference", error);
      }
    },
    toggleTheme: async () => {
      const newMode = get().themeMode === "light" ? "dark" : "light";
      set((state) => {
        state.themeMode = newMode;
      });
      try {
        await api.put("/api/v1/users/me/preferences", { theme: newMode });
      } catch (error) {
        console.error("Failed to save preference", error);
      }
    },
    fetchPreferences: async () => {
      try {
        const response = await api.get("/api/v1/users/me/preferences");
        if (response.data && response.data.theme) {
          set((state) => {
            state.themeMode = response.data.theme;
          });
        }
      } catch (error) {
        console.error("Failed to fetch preferences", error);
      }
    },
  })),
);
