import { renderHook } from "@testing-library/react";
import { useCreateWBE, useUpdateWBE, useDeleteWBE } from "./useWBEs";
import { WbEsService } from "@/api/generated";
import { request as __request } from "@/api/generated/core/request";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TimeMachineProvider } from "@/contexts/TimeMachineContext";
import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock dependencies
vi.mock("@/api/generated/services/WbEsService");
vi.mock("@/api/generated/core/request");

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <TimeMachineProvider>{children}</TimeMachineProvider>
    </QueryClientProvider>
  );
};

describe("useWBEs Hooks with Time Machine", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store
    const store = useTimeMachineStore.getState();
    // Use actions instead of direct property assignment which is readonly in Immer
    store.setCurrentProject("proj-123");
    store.clearProjectSettings("proj-123");
    store.resetToNow();
  });

  it("should inject control_date into useCreateWBE payload when time is selected", async () => {
    const store = useTimeMachineStore.getState();
    const testDate = new Date("2025-01-01T12:00:00Z");
    store.selectTime(testDate);

    const { result } = renderHook(() => useCreateWBE(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      project_id: "proj-123",
      code: "TEST",
      name: "Test WBE",
    });

    expect(WbEsService.createWbe).toHaveBeenCalledWith(
      expect.objectContaining({
        project_id: "proj-123",
        code: "TEST",
        name: "Test WBE",
        control_date: testDate.toISOString(),
      })
    );
  });

  it("should NOT inject control_date into useCreateWBE payload when NO time is selected", async () => {
    const { result } = renderHook(() => useCreateWBE(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      project_id: "proj-123",
      code: "TEST",
      name: "Test WBE",
    });

    expect(WbEsService.createWbe).toHaveBeenCalledWith(
      expect.objectContaining({
        project_id: "proj-123",
        code: "TEST",
        name: "Test WBE",
        control_date: null,
      })
    );
  });

  it("should inject control_date into useUpdateWBE payload", async () => {
    const store = useTimeMachineStore.getState();
    const testDate = new Date("2025-01-01T12:00:00Z");
    store.selectTime(testDate);

    const { result } = renderHook(() => useUpdateWBE(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      id: "wbe-123",
      data: { name: "Updated Name" },
    });

    expect(WbEsService.updateWbe).toHaveBeenCalledWith(
      "wbe-123",
      expect.objectContaining({
        name: "Updated Name",
        control_date: testDate.toISOString(),
      })
    );
  });

  it("should pass control_date as query param in useDeleteWBE", async () => {
    const store = useTimeMachineStore.getState();
    const testDate = new Date("2025-01-01T12:00:00Z");
    store.selectTime(testDate);

    const { result } = renderHook(() => useDeleteWBE(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync("wbe-123");

    expect(__request).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        method: "DELETE",
        url: "/api/v1/wbes/{wbe_id}",
        query: { control_date: testDate.toISOString() },
      })
    );
  });
});
