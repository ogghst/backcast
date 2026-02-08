import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChangeOrderSummaryCard } from "./ChangeOrderSummaryCard";
import type { ChangeOrderPublic } from "@/api/generated";

// Mock the workflow info hook
vi.mock("../hooks/useWorkflowInfo", () => ({
  useWorkflowInfo: vi.fn(() => ({
    isBranchLocked: false,
    lockedBranchWarning: null,
  })),
}));

const mockChangeOrder: ChangeOrderPublic = {
  id: "BR-123",
  change_order_id: "BR-123",
  code: "CO-2026-001",
  title: "Test Change Order",
  status: "Draft",
  description: "Test description",
  justification: "Test justification",
  effective_date: "2026-01-15",
  project_id: "proj-123",
  branch: "BR-CO-2026-001",
  branch_locked: false,
  available_transitions: ["Submitted"],
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  created_by: "user-123",
  can_edit_status: true,
};

describe("ChangeOrderSummaryCard", () => {
  it("renders change order details correctly", () => {
    const onEdit = vi.fn();
    render(
      <ChangeOrderSummaryCard
        changeOrder={mockChangeOrder}
        onEdit={onEdit}
      />
    );

    expect(screen.getByText("CO-2026-001")).toBeInTheDocument();
    expect(screen.getByText("Test Change Order")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getByText("2026-01-15")).toBeInTheDocument();
    expect(screen.getByText("Test description")).toBeInTheDocument();
  });

  it("calls onEdit when edit button is clicked", () => {
    const onEdit = vi.fn();
    render(
      <ChangeOrderSummaryCard
        changeOrder={mockChangeOrder}
        onEdit={onEdit}
      />
    );

    fireEvent.click(screen.getByText("Edit"));
    expect(onEdit).toHaveBeenCalled();
  });
});
