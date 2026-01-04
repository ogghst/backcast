import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { StandardTable, TableParams } from "./StandardTable";
import { TablePaginationConfig } from "antd";

describe("StandardTable", () => {
  const mockOnChange = vi.fn();
  const mockData = [
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

  it("renders table with data", () => {
    // @ts-expect-error - Testing missing prop
    render(<StandardTable {...defaultProps} />);
    expect(screen.getByText("Item 1")).toBeInTheDocument();
  });

  it("calls onChange when pagination changes", () => {
    // @ts-expect-error - Testing missing prop
    render(<StandardTable {...defaultProps} />);

    // Find the pagination "next" button or page 2
    const page2Button = screen.getByTitle("2");
    fireEvent.click(page2Button);

    expect(mockOnChange).toHaveBeenCalled();
    const args = mockOnChange.mock.calls[0];
    const pagination = args[0] as TablePaginationConfig;
    expect(pagination.current).toBe(2);
  });

  it("shows loading state", () => {
    // @ts-expect-error - Testing missing prop
    render(<StandardTable {...defaultProps} loading={true} />);
    // AntD table spinner usually has class or aria
    // For simplicity, we just check if rows are replaced by loading or spinner exists
    // But testing-library might find the rows if they are just grayed out.
    // Let's rely on AntD internal implementation validation?
    // Actually, snapshotting or checking for specific spinner class is brittle.
    // We trust AntD works, we just verify we passed the prop.
    // A better test for wrapper is strictly verifying props passing if we mocked Table.
    // But integration testing is fine.

    // Check if loading overlay or spinner exists.
    // AntD uses .ant-spin
    expect(document.querySelector(".ant-spin")).toBeInTheDocument();
  });
});
