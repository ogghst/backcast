import { describe, it, expect, beforeEach } from "vitest";
import { useTimeMachineStore } from "./useTimeMachineStore";
import { act } from "@testing-library/react";

describe("useTimeMachineStore", () => {
  beforeEach(() => {
    // Reset store state before each test
    act(() => {
      useTimeMachineStore.setState({
        currentProjectId: null,
        isExpanded: false,
        projectSettings: {},
      });
    });
  });

  describe("Project Context", () => {
    it("sets current project without start date", () => {
      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-1");
      });

      const state = useTimeMachineStore.getState();
      expect(state.currentProjectId).toBe("project-1");
      expect(state.projectSettings["project-1"]).toEqual({
        selectedTime: null,
        selectedBranch: "main",
        viewMode: "merged",
      });
    });

    it("sets current project with start date", () => {
      const startDate = new Date("2024-01-01");

      act(() => {
        useTimeMachineStore
          .getState()
          .setCurrentProject("project-1", startDate);
      });

      const state = useTimeMachineStore.getState();
      expect(state.currentProjectId).toBe("project-1");
      expect(state.projectSettings["project-1"].selectedTime).toBe(
        startDate.toISOString()
      );
      expect(state.projectSettings["project-1"].selectedBranch).toBe("main");
    });

    it("preserves existing project settings when switching back", () => {
      const customDate = new Date("2025-06-15");

      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-1");
        useTimeMachineStore.getState().selectTime(customDate);
        useTimeMachineStore.getState().selectBranch("feature-branch");
      });

      // Switch to different project
      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-2");
      });

      // Switch back to project-1
      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-1");
      });

      const state = useTimeMachineStore.getState();
      expect(state.projectSettings["project-1"].selectedTime).toBe(
        customDate.toISOString()
      );
      expect(state.projectSettings["project-1"].selectedBranch).toBe(
        "feature-branch"
      );
    });

    it("clears current project", () => {
      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-1");
        useTimeMachineStore.getState().setCurrentProject(null);
      });

      const state = useTimeMachineStore.getState();
      expect(state.currentProjectId).toBeNull();
    });
  });

  describe("Time Selection", () => {
    beforeEach(() => {
      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-1");
      });
    });

    it("selects a specific time", () => {
      const selectedDate = new Date("2025-03-15T10:30:00Z");

      act(() => {
        useTimeMachineStore.getState().selectTime(selectedDate);
      });

      const state = useTimeMachineStore.getState();
      expect(state.getSelectedTime()).toBe(selectedDate.toISOString());
    });

    it("resets to now (null)", () => {
      const selectedDate = new Date("2025-03-15");

      act(() => {
        useTimeMachineStore.getState().selectTime(selectedDate);
        useTimeMachineStore.getState().resetToNow();
      });

      const state = useTimeMachineStore.getState();
      expect(state.getSelectedTime()).toBeNull();
    });

    it("handles null time selection", () => {
      act(() => {
        useTimeMachineStore.getState().selectTime(null);
      });

      const state = useTimeMachineStore.getState();
      expect(state.getSelectedTime()).toBeNull();
    });
  });

  describe("Branch Selection", () => {
    beforeEach(() => {
      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-1");
      });
    });

    it("selects a branch", () => {
      act(() => {
        useTimeMachineStore.getState().selectBranch("feature-branch");
      });

      const state = useTimeMachineStore.getState();
      expect(state.getSelectedBranch()).toBe("feature-branch");
    });

    it("defaults to main branch", () => {
      const state = useTimeMachineStore.getState();
      expect(state.getSelectedBranch()).toBe("main");
    });
  });

  describe("View Mode Selection", () => {
    beforeEach(() => {
      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-1");
      });
    });

    it("selects merged view mode", () => {
      act(() => {
        useTimeMachineStore.getState().selectViewMode("merged");
      });

      const state = useTimeMachineStore.getState();
      expect(state.getViewMode()).toBe("merged");
    });

    it("selects isolated view mode", () => {
      act(() => {
        useTimeMachineStore.getState().selectViewMode("isolated");
      });

      const state = useTimeMachineStore.getState();
      expect(state.getViewMode()).toBe("isolated");
    });

    it("defaults to merged view mode", () => {
      const state = useTimeMachineStore.getState();
      expect(state.getViewMode()).toBe("merged");
    });

    it("preserves view mode when switching projects", () => {
      // Set project 1 to isolated mode
      act(() => {
        useTimeMachineStore.getState().selectViewMode("isolated");
      });

      // Switch to project 2 (should have default merged mode)
      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-2");
      });

      expect(useTimeMachineStore.getState().getViewMode()).toBe("merged");

      // Switch back to project 1 (should preserve isolated mode)
      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-1");
      });

      expect(useTimeMachineStore.getState().getViewMode()).toBe("isolated");
    });
  });

  describe("UI State", () => {
    it("toggles expanded state", () => {
      expect(useTimeMachineStore.getState().isExpanded).toBe(false);

      act(() => {
        useTimeMachineStore.getState().toggleExpanded();
      });

      expect(useTimeMachineStore.getState().isExpanded).toBe(true);

      act(() => {
        useTimeMachineStore.getState().toggleExpanded();
      });

      expect(useTimeMachineStore.getState().isExpanded).toBe(false);
    });
  });

  describe("Project Settings Management", () => {
    it("clears project settings", () => {
      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-1");
        useTimeMachineStore.getState().selectTime(new Date("2025-01-01"));
        useTimeMachineStore.getState().selectBranch("custom-branch");
      });

      expect(
        useTimeMachineStore.getState().projectSettings["project-1"]
      ).toBeDefined();

      act(() => {
        useTimeMachineStore.getState().clearProjectSettings("project-1");
      });

      expect(
        useTimeMachineStore.getState().projectSettings["project-1"]
      ).toBeUndefined();
    });
  });

  describe("Getters", () => {
    it("returns null for selected time when no project is set", () => {
      const state = useTimeMachineStore.getState();
      expect(state.getSelectedTime()).toBeNull();
    });

    it("returns default branch when no project is set", () => {
      const state = useTimeMachineStore.getState();
      expect(state.getSelectedBranch()).toBe("main");
    });

    it("returns default view mode when no project is set", () => {
      const state = useTimeMachineStore.getState();
      expect(state.getViewMode()).toBe("merged");
    });

    it("returns project-specific settings", () => {
      const date = new Date("2025-05-20");

      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-1");
        useTimeMachineStore.getState().selectTime(date);
        useTimeMachineStore.getState().selectBranch("dev");
        useTimeMachineStore.getState().selectViewMode("isolated");
      });

      const state = useTimeMachineStore.getState();
      expect(state.getSelectedTime()).toBe(date.toISOString());
      expect(state.getSelectedBranch()).toBe("dev");
      expect(state.getViewMode()).toBe("isolated");
    });
  });

  describe("Multiple Projects", () => {
    it("maintains separate settings for different projects", () => {
      const date1 = new Date("2024-01-01");
      const date2 = new Date("2025-12-31");

      // Set up project 1
      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-1");
        useTimeMachineStore.getState().selectTime(date1);
        useTimeMachineStore.getState().selectBranch("main");
        useTimeMachineStore.getState().selectViewMode("merged");
      });

      // Set up project 2
      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-2");
        useTimeMachineStore.getState().selectTime(date2);
        useTimeMachineStore.getState().selectBranch("feature");
        useTimeMachineStore.getState().selectViewMode("isolated");
      });

      // Verify project 2 settings
      let state = useTimeMachineStore.getState();
      expect(state.getSelectedTime()).toBe(date2.toISOString());
      expect(state.getSelectedBranch()).toBe("feature");
      expect(state.getViewMode()).toBe("isolated");

      // Switch back to project 1
      act(() => {
        useTimeMachineStore.getState().setCurrentProject("project-1");
      });

      // Verify project 1 settings are preserved
      state = useTimeMachineStore.getState();
      expect(state.getSelectedTime()).toBe(date1.toISOString());
      expect(state.getSelectedBranch()).toBe("main");
      expect(state.getViewMode()).toBe("merged");
    });
  });
});
