import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { createResourceHooks } from "./useCrud";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";

// Setup Wrapper
const createWrapper = () => {
  const queryClient = new QueryClient();
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// Mock API
const mockApi = {
  getUsers: vi.fn(),
  getUser: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
};

describe("createResourceHooks", () => {
  const { useList, useCreate } = createResourceHooks("users", mockApi, {
    invalidation: {
      update: ["users", "evm_calculations"],
    },
  });

  it("useList fetches data", async () => {
    mockApi.getUsers.mockResolvedValue([{ id: 1, name: "Alice" }]);

    const { result } = renderHook(() => useList(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([{ id: 1, name: "Alice" }]);
  });

  // Since we can't easily test actual invalidation without a complex integration test,
  // we primarily test that the mutation calls the API.
  // Integration tests will handle side effects or we can spy on queryClient.invalidateQueries if we export it.

  it("useCreate calls api", async () => {
    mockApi.createUser.mockResolvedValue({ id: 2, name: "Bob" });
    const { result } = renderHook(() => useCreate(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ name: "Bob" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApi.createUser).toHaveBeenCalledWith({ name: "Bob" });
  });
});
