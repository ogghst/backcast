import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { MemoryRouter, useSearchParams } from "react-router-dom";
import { useTableParams } from "./useTableParams";
import type { TablePaginationConfig } from "antd/es/table";

// Helper to inspect URL params
const useURLParams = () => {
  const [params] = useSearchParams();
  return params;
};

describe("useTableParams", () => {
  it("should initialize params from URL", () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <MemoryRouter
        initialEntries={[
          "/users?page=2&per_page=20&search=test&filters=role:admin",
        ]}
      >
        {children}
      </MemoryRouter>
    );

    const { result } = renderHook(() => useTableParams(), { wrapper });

    expect(result.current.tableParams).toMatchObject({
      pagination: {
        current: 2,
        pageSize: 20,
      },
      search: "test",
      filters: { role: ["admin"] },
    });
  });

  it("should update URL when params change (pagination & sort)", () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <MemoryRouter initialEntries={["/users"]}>{children}</MemoryRouter>
    );

    const { result } = renderHook(() => useTableParams(), { wrapper });

    act(() => {
      result.current.handleTableChange({ current: 2, pageSize: 20 }, {}, {
        field: "name",
        order: "ascend",
      } as TablePaginationConfig);
    });

    expect(result.current.tableParams.pagination.current).toBe(2);
    expect(result.current.tableParams.sortField).toBe("name");
    expect(result.current.tableParams.sortOrder).toBe("ascend");
  });

  it("should update URL when filters change", () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <MemoryRouter initialEntries={["/users"]}>{children}</MemoryRouter>
    );

    const { result } = renderHook(
      () => {
        const { tableParams, handleTableChange } = useTableParams();
        const params = useURLParams();
        return { tableParams, handleTableChange, params };
      },
      { wrapper }
    );

    act(() => {
      result.current.handleTableChange(
        { current: 1, pageSize: 10 },
        { role: ["admin", "user"], status: ["active"] },
        {}
      );
    });

    expect(result.current.params.get("filters")).toBe(
      "role:admin,user;status:active"
    );
    expect(result.current.tableParams.filters).toEqual({
      role: ["admin", "user"],
      status: ["active"],
    });
  });

  it("should update URL when search changes", () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <MemoryRouter initialEntries={["/users?page=5"]}>{children}</MemoryRouter>
    );

    const { result } = renderHook(
      () => {
        const { tableParams, handleSearch } = useTableParams();
        const params = useURLParams();
        return { tableParams, handleSearch, params };
      },
      { wrapper }
    );

    act(() => {
      result.current.handleSearch("new search");
    });

    expect(result.current.params.get("search")).toBe("new search");
    expect(result.current.params.get("page")).toBe("1"); // Should reset page
    expect(result.current.tableParams.search).toBe("new search");
  });

  it("should handle typed generic filters", () => {
    interface TestEntity {
      id: string;
      status: string;
    }
    interface TestFilters extends Record<string, string[] | null> {
      status: string[] | null;
    }

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <MemoryRouter initialEntries={["/users"]}>{children}</MemoryRouter>
    );

    const { result } = renderHook(
      () => useTableParams<TestEntity, TestFilters>(),
      { wrapper }
    );

    act(() => {
      // @ts-expect-error - 'invalidHelper' is not in TestFilters
      // This test actually just verifies runtime behavior, but explicitly using generics
      // helps ensure no compilation errors in the hook usage.
      result.current.handleTableChange(
        {},
        { status: ["active"] }, // Valid filter
        {}
      );
    });

    expect(result.current.tableParams.filters?.status).toEqual(["active"]);
  });
});
