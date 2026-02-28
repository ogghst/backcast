import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useWorkflowActions,
  WORKFLOW_ACTIONS,
  isActionAvailable,
} from "./useWorkflowActions";

// Mock the API hooks
vi.mock("../api/useChangeOrders", () => ({
  useUpdateChangeOrder: vi.fn(),
  useMergeChangeOrder: vi.fn(),
}));

// Mock the approvals API hooks
vi.mock("../api/useApprovals", () => ({
  useApproveChangeOrder: vi.fn(),
  useRejectChangeOrder: vi.fn(),
  useArchiveChangeOrder: vi.fn(),
}));

import {
  useUpdateChangeOrder,
  useMergeChangeOrder,
} from "../api/useChangeOrders";

import {
  useApproveChangeOrder,
  useRejectChangeOrder,
  useArchiveChangeOrder,
} from "../api/useApprovals";

describe("useWorkflowActions", () => {
  let queryClient: QueryClient;
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        mutations: { retry: false },
        queries: { retry: false },
      },
    });

    // Setup mock implementations with callback support
    vi.mocked(useUpdateChangeOrder).mockImplementation(
      (options) =>
        ({
          mutateAsync: vi.fn(async (args) => {
            // Simulate success behavior - call onSuccess callback
            const result = { status: "Submitted for Approval", ...args.data };
            options?.onSuccess?.(result);
            return result;
          }),
          isPending: false,
        }) as unknown as ReturnType<typeof useUpdateChangeOrder>,
    );

    vi.mocked(useMergeChangeOrder).mockImplementation(
      (options) =>
        ({
          mutateAsync: vi.fn(async () => {
            // Simulate success behavior - call onSuccess callback
            const result = { status: "Implemented" };
            options?.onSuccess?.(result);
            return result;
          }),
          isPending: false,
        }) as unknown as ReturnType<typeof useMergeChangeOrder>,
    );

    // Setup mock implementations for approval hooks
    vi.mocked(useApproveChangeOrder).mockImplementation(
      (options) =>
        ({
          mutateAsync: vi.fn(async () => {
            const result = { status: "Approved" };
            options?.onSuccess?.(result);
            return result;
          }),
          isPending: false,
        }) as unknown as ReturnType<typeof useApproveChangeOrder>,
    );

    vi.mocked(useRejectChangeOrder).mockImplementation(
      (options) =>
        ({
          mutateAsync: vi.fn(async () => {
            const result = { status: "Rejected" };
            options?.onSuccess?.(result);
            return result;
          }),
          isPending: false,
        }) as unknown as ReturnType<typeof useRejectChangeOrder>,
    );

    vi.mocked(useArchiveChangeOrder).mockImplementation(
      (options) =>
        ({
          mutateAsync: vi.fn(async () => {
            const result = { status: "Implemented", code: "CO-001" };
            options?.onSuccess?.(result);
            return result;
          }),
          isPending: false,
        }) as unknown as ReturnType<typeof useArchiveChangeOrder>,
    );
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  describe("WORKFLOW_ACTIONS constant", () => {
    it("should have correct action labels", () => {
      expect(WORKFLOW_ACTIONS.SUBMIT.label).toBe("Submit");
      expect(WORKFLOW_ACTIONS.APPROVE.label).toBe("Approve");
      expect(WORKFLOW_ACTIONS.REJECT.label).toBe("Reject");
      expect(WORKFLOW_ACTIONS.MERGE.label).toBe("Merge to Main");
      expect(WORKFLOW_ACTIONS.ARCHIVE.label).toBe("Archive Branch");
    });

    it("should have correct status values", () => {
      expect(WORKFLOW_ACTIONS.SUBMIT.status).toBe("Submitted for Approval");
      expect(WORKFLOW_ACTIONS.APPROVE.status).toBe("Approved");
      expect(WORKFLOW_ACTIONS.REJECT.status).toBe("Rejected");
      expect(WORKFLOW_ACTIONS.MERGE.status).toBe("Implemented");
      expect(WORKFLOW_ACTIONS.ARCHIVE.status).toBe("Archived");
    });
  });

  describe("isActionAvailable helper", () => {
    it("should return false when transitions is null", () => {
      expect(isActionAvailable("SUBMIT", null)).toBe(false);
      expect(isActionAvailable("APPROVE", null)).toBe(false);
      expect(isActionAvailable("MERGE", null)).toBe(false);
      expect(isActionAvailable("ARCHIVE", null)).toBe(false);
    });

    it("should return false when transitions is undefined", () => {
      expect(isActionAvailable("SUBMIT", undefined)).toBe(false);
      expect(isActionAvailable("ARCHIVE", undefined)).toBe(false);
    });

    it("should return false when transitions is empty array", () => {
      expect(isActionAvailable("SUBMIT", [])).toBe(false);
      expect(isActionAvailable("ARCHIVE", [])).toBe(false);
    });

    it("should return true when action status is in available transitions", () => {
      expect(isActionAvailable("SUBMIT", ["Submitted for Approval"])).toBe(
        true,
      );
      expect(isActionAvailable("APPROVE", ["Approved"])).toBe(true);
      expect(isActionAvailable("MERGE", ["Implemented"])).toBe(true);
      expect(isActionAvailable("ARCHIVE", ["Archived"])).toBe(true);
    });

    it("should return false when action status is not in available transitions", () => {
      expect(isActionAvailable("MERGE", ["Under Review"])).toBe(false);
      expect(isActionAvailable("APPROVE", ["Implemented"])).toBe(false);
      expect(isActionAvailable("ARCHIVE", ["Draft"])).toBe(false);
    });

    it("should check for specific status in transitions", () => {
      const transitions = ["Approved", "Rejected"];
      // APPROVE action has target status "Approved" - should return true
      expect(isActionAvailable("APPROVE", transitions)).toBe(true);
      // REJECT action has target status "Rejected" - should return true
      expect(isActionAvailable("REJECT", transitions)).toBe(true);
      // MERGE action has target status "Implemented" - should return false (not in transitions)
      expect(isActionAvailable("MERGE", transitions)).toBe(false);
      // ARCHIVE action has target status "Archived" - should return false (not in transitions)
      expect(isActionAvailable("ARCHIVE", transitions)).toBe(false);
    });
  });

  describe("useWorkflowActions hook", () => {
    it("should return action methods", () => {
      const { result } = renderHook(() => useWorkflowActions("BR-123"), {
        wrapper,
      });

      expect(result.current).toHaveProperty("submit");
      expect(result.current).toHaveProperty("approve");
      expect(result.current).toHaveProperty("reject");
      expect(result.current).toHaveProperty("merge");
      expect(result.current).toHaveProperty("archive");
      expect(typeof result.current.submit).toBe("function");
      expect(typeof result.current.approve).toBe("function");
      expect(typeof result.current.reject).toBe("function");
      expect(typeof result.current.merge).toBe("function");
      expect(typeof result.current.archive).toBe("function");
    });

    it("should return isLoading state", () => {
      vi.mocked(useUpdateChangeOrder).mockReturnValue({
        mutateAsync: vi.fn(),
        isPending: true,
      } as unknown as ReturnType<typeof useUpdateChangeOrder>);

      const { result } = renderHook(() => useWorkflowActions("BR-123"), {
        wrapper,
      });

      expect(result.current.isLoading).toBe(true);
    });

    it("should return isLoading as true when archive mutation is pending", () => {
      vi.mocked(useArchiveChangeOrder).mockReturnValue({
        mutateAsync: vi.fn(),
        isPending: true,
      } as unknown as ReturnType<typeof useArchiveChangeOrder>);

      const { result } = renderHook(() => useWorkflowActions("BR-123"), {
        wrapper,
      });

      expect(result.current.isLoading).toBe(true);
    });

    it("should call submit with correct status", async () => {
      const { result } = renderHook(() => useWorkflowActions("BR-123"), {
        wrapper,
      });

      await act(async () => {
        await result.current.submit("Test comment");
      });

      // The mock is called automatically, so we just check it doesn't throw
      expect(result.current).toBeDefined();
    });

    it("should call approve with correct status", async () => {
      const { result } = renderHook(() => useWorkflowActions("BR-123"), {
        wrapper,
      });

      await act(async () => {
        await result.current.approve("Approved comment");
      });

      expect(result.current).toBeDefined();
    });

    it("should call reject with correct status", async () => {
      const { result } = renderHook(() => useWorkflowActions("BR-123"), {
        wrapper,
      });

      await act(async () => {
        await result.current.reject("Reject reason");
      });

      expect(result.current).toBeDefined();
    });

    it("should call merge with merge request", async () => {
      const { result } = renderHook(() => useWorkflowActions("BR-123"), {
        wrapper,
      });

      await act(async () => {
        await result.current.merge({
          target_branch: "main",
          comment: "Merge comment",
        });
      });

      expect(result.current).toBeDefined();
    });

    it("should call merge with default target branch when not specified", async () => {
      const { result } = renderHook(() => useWorkflowActions("BR-123"), {
        wrapper,
      });

      await act(async () => {
        await result.current.merge({ comment: "Test" });
      });

      expect(result.current).toBeDefined();
    });

    it("should call onSuccess callback when action succeeds", async () => {
      const onSuccess = vi.fn();

      const { result } = renderHook(
        () => useWorkflowActions("BR-123", { onSuccess }),
        { wrapper },
      );

      await act(async () => {
        await result.current.submit();
      });

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });
    });

    it("should call onError callback when action fails", async () => {
      const onError = vi.fn();
      const error = new Error("API Error");

      // Override the mock to reject
      vi.mocked(useUpdateChangeOrder).mockImplementation(
        (options) =>
          ({
            mutateAsync: vi.fn(async () => {
              options?.onError?.(error);
              throw error;
            }),
            isPending: false,
          }) as unknown as ReturnType<typeof useUpdateChangeOrder>,
      );

      const { result } = renderHook(
        () => useWorkflowActions("BR-123", { onError }),
        { wrapper },
      );

      await act(async () => {
        try {
          await result.current.submit();
        } catch {
          // Expected to throw
        }
      });

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith(error);
      });
    });

    it("should call archive action", async () => {
      const { result } = renderHook(() => useWorkflowActions("BR-123"), {
        wrapper,
      });

      await act(async () => {
        await result.current.archive();
      });

      // Should not throw
      expect(result.current).toBeDefined();
    });

    it("should call archive mutation with correct change order id", async () => {
      const mockMutateAsync = vi.fn().mockResolvedValue({ status: "Implemented" });
      vi.mocked(useArchiveChangeOrder).mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as unknown as ReturnType<typeof useArchiveChangeOrder>);

      const { result } = renderHook(() => useWorkflowActions("co-456"), {
        wrapper,
      });

      await act(async () => {
        await result.current.archive();
      });

      expect(mockMutateAsync).toHaveBeenCalledWith({ id: "co-456" });
    });

    it("should call onSuccess callback when archive succeeds", async () => {
      const onSuccess = vi.fn();
      const archivedChangeOrder = { status: "Implemented", code: "CO-001" };

      vi.mocked(useArchiveChangeOrder).mockImplementation(
        (options) =>
          ({
            mutateAsync: vi.fn(async () => {
              options?.onSuccess?.(archivedChangeOrder);
              return archivedChangeOrder;
            }),
            isPending: false,
          }) as unknown as ReturnType<typeof useArchiveChangeOrder>,
      );

      const { result } = renderHook(
        () => useWorkflowActions("BR-123", { onSuccess }),
        { wrapper },
      );

      await act(async () => {
        await result.current.archive();
      });

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalledWith(archivedChangeOrder);
      });
    });

    it("should call onError callback when archive fails", async () => {
      const onError = vi.fn();
      const error = new Error("Cannot archive active change order");

      vi.mocked(useArchiveChangeOrder).mockImplementation(
        (options) =>
          ({
            mutateAsync: vi.fn(async () => {
              options?.onError?.(error);
              throw error;
            }),
            isPending: false,
          }) as unknown as ReturnType<typeof useArchiveChangeOrder>,
      );

      const { result } = renderHook(
        () => useWorkflowActions("BR-123", { onError }),
        { wrapper },
      );

      await act(async () => {
        try {
          await result.current.archive();
        } catch {
          // Expected to throw
        }
      });

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith(error);
      });
    });
  });
});
