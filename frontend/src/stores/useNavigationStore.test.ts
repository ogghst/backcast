import { describe, it, expect, beforeEach } from "vitest";
import { act } from "@testing-library/react";
import { useNavigationStore } from "./useNavigationStore";

describe("useNavigationStore", () => {
  beforeEach(() => {
    // Reset to defaults before each test.
    act(() => {
      useNavigationStore.setState({
        expanded: false,
        mobileOpen: false,
        flyout: null,
      });
    });
  });

  describe("default state", () => {
    it("starts collapsed (rail), drawer closed, no flyout", () => {
      const state = useNavigationStore.getState();
      expect(state.expanded).toBe(false);
      expect(state.mobileOpen).toBe(false);
      expect(state.flyout).toBeNull();
    });
  });

  describe("toggleExpanded", () => {
    it("flips expanded false → true", () => {
      act(() => {
        useNavigationStore.getState().toggleExpanded();
      });
      expect(useNavigationStore.getState().expanded).toBe(true);
    });

    it("flips expanded true → false", () => {
      act(() => {
        useNavigationStore.getState().toggleExpanded();
        useNavigationStore.getState().toggleExpanded();
      });
      expect(useNavigationStore.getState().expanded).toBe(false);
    });

    it("does not touch mobileOpen / flyout", () => {
      act(() => {
        useNavigationStore.getState().setMobileOpen(true);
        useNavigationStore.getState().setFlyout("chat");
        useNavigationStore.getState().toggleExpanded();
      });
      const state = useNavigationStore.getState();
      expect(state.mobileOpen).toBe(true);
      expect(state.flyout).toBe("chat");
    });
  });

  describe("setMobileOpen", () => {
    it("opens and closes the drawer", () => {
      act(() => {
        useNavigationStore.getState().setMobileOpen(true);
      });
      expect(useNavigationStore.getState().mobileOpen).toBe(true);

      act(() => {
        useNavigationStore.getState().setMobileOpen(false);
      });
      expect(useNavigationStore.getState().mobileOpen).toBe(false);
    });
  });

  describe("setFlyout", () => {
    it.each(["chat", "account", "entity"] as const)(
      "sets flyout to %s",
      (f) => {
        act(() => {
          useNavigationStore.getState().setFlyout(f);
        });
        expect(useNavigationStore.getState().flyout).toBe(f);
      },
    );

    it("clears flyout with null", () => {
      act(() => {
        useNavigationStore.getState().setFlyout("account");
        useNavigationStore.getState().setFlyout(null);
      });
      expect(useNavigationStore.getState().flyout).toBeNull();
    });
  });

  describe("persistence (partialize)", () => {
    it("persists ONLY expanded (not mobileOpen / flyout)", () => {
      // Drive all three pieces of state away from defaults.
      act(() => {
        useNavigationStore.getState().toggleExpanded(); // expanded = true
        useNavigationStore.getState().setMobileOpen(true);
        useNavigationStore.getState().setFlyout("chat");
      });

      // The persist middleware exposes its config on the store's internals.
      // `persist.getOptions().partialize` is the function we configured.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const partialize = (useNavigationStore as any).persist?.getOptions?.()
        ?.partialize as
        | ((s: ReturnType<typeof useNavigationStore.getState>) => unknown)
        | undefined;

      expect(partialize).toBeTypeOf("function");

      const persisted = partialize!(useNavigationStore.getState()) as Record<
        string,
        unknown
      >;

      // Only `expanded` is in the persisted shape.
      expect(Object.keys(persisted).sort()).toEqual(["expanded"]);
      expect(persisted.expanded).toBe(true);
      expect(persisted).not.toHaveProperty("mobileOpen");
      expect(persisted).not.toHaveProperty("flyout");
    });

    it("storage key is backcast-nav", () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const name = (useNavigationStore as any).persist?.getOptions?.()
        ?.name as string | undefined;
      expect(name).toBe("backcast-nav");
    });
  });
});
