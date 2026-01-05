import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useTableParams } from "./useTableParams";

// Mock container for router context
const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <MemoryRouter initialEntries={["/users?page=1&per_page=10"]}>
    {children}
  </MemoryRouter>
);

describe("useTableParams", () => {
  it("should initialize params from URL", () => {
    const { result } = renderHook(() => useTableParams(), { wrapper: Wrapper });

    expect(result.current.tableParams).toEqual({
      pagination: {
        current: 1,
        pageSize: 10,
      },
    });
  });

  it("should update URL when params change", () => {
    const { result } = renderHook(() => useTableParams(), { wrapper: Wrapper });

    act(() => {
      // Mock Ant Design Table pagination change
      result.current.handleTableChange(
        { current: 2, pageSize: 20 },
        {},
        {},
        { currentDataSource: [], action: "paginate" },
      );
    });

    expect(result.current.tableParams.pagination.current).toBe(2);
    expect(result.current.tableParams.pagination.pageSize).toBe(20);
  });
});
