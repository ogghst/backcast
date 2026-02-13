import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { StandardTable, TableParams } from "./StandardTable";
import { TablePaginationConfig } from "antd";

interface TestItem {
  id: string;
  name: string;
}

describe("StandardTable", () => {
  const mockOnChange = vi.fn();
  const mockData: TestItem[] = [
    { id: "1", name: "Item 1" },
    { id: "2", name: "Item 2" },
  ];
  const columns = [{ title: "Name", dataIndex: "name", key: "name" }];
  const tableParams: TableParams = {
    pagination: { current: 1, pageSize: 10, total: 20 },
  };

  const defaultProps = {
    rowKey: "id",
    columns,
    dataSource: mockData,
    loading: false,
    tableParams,
    onChange: mockOnChange,
  };

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders table with data", () => {
    render(<StandardTable<TestItem> {...defaultProps} />);
    expect(screen.getByText("Item 1")).toBeInTheDocument();
  });

  it("calls onChange when pagination changes", () => {
    render(<StandardTable<TestItem> {...defaultProps} />);

    // Find the pagination "next" button or page 2
    const page2Button = screen.getByTitle("2");
    fireEvent.click(page2Button);

    expect(mockOnChange).toHaveBeenCalled();
    const args = mockOnChange.mock.calls[0];
    const pagination = args[0] as TablePaginationConfig;
    expect(pagination.current).toBe(2);
  });

  it("shows loading state", () => {
    render(<StandardTable<TestItem> {...defaultProps} loading={true} />);
    expect(document.querySelector(".ant-spin")).toBeInTheDocument();
  });

  it("renders search input when searchable is true", () => {
    render(
      <StandardTable<TestItem>
        {...defaultProps}
        searchable={true}
        searchPlaceholder="Test Search"
      />
    );
    expect(screen.getByPlaceholderText("Test Search")).toBeInTheDocument();
  });

  it("calls onSearch with debounce when typing", () => {
    const mockOnSearch = vi.fn();
    render(
      <StandardTable<TestItem>
        {...defaultProps}
        searchable={true}
        onSearch={mockOnSearch}
      />
    );

    const input = screen.getByPlaceholderText("Search...");
    fireEvent.change(input, { target: { value: "test query" } });

    // Should not be called immediately
    expect(mockOnSearch).not.toHaveBeenCalled();

    // Fast-forward time
    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(mockOnSearch).toHaveBeenCalledWith("test query");
  });
});
