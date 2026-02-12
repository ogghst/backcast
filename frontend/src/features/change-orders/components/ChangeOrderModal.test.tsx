import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ChangeOrderModal } from "./ChangeOrderModal";
import type { ChangeOrderPublic } from "@/api/generated";

// Mock matchedMedia for AntD modal
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock the workflow info hook
vi.mock("../hooks/useWorkflowInfo", () => ({
  useWorkflowInfo: vi.fn(() => ({
    isBranchLocked: false,
    lockedBranchWarning: null,
    statusOptions: [
      { label: "Draft", value: "Draft" },
      { label: "Submitted", value: "Submitted" },
    ],
    isStatusDisabled: false,
  })),
}));

const mockChangeOrder: ChangeOrderPublic = {
  id: "BR-123",
  change_order_id: "BR-123",
  code: "CO-2026-001",
  title: "Test Change Order",
  status: "Draft",
  description: "Test description with enough characters for validation",
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

describe("ChangeOrderModal", () => {
  const onOk = vi.fn();
  const onCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders correctly in create mode", async () => {
    render(
      <ChangeOrderModal
        open={true}
        onOk={onOk}
        onCancel={onCancel}
        confirmLoading={false}
        projectId="proj-123"
        existingCodes={[]}
      />
    );

    // Wait for modal to be visible with longer timeout
    await waitFor(() => {
        expect(screen.getByText("Create Change Order")).toBeInTheDocument();
    }, { timeout: 3000 });
    
    expect(screen.getByLabelText("Change Order Code")).toBeInTheDocument();
    // Check for auto-generated code CO-{Year}-001
    const currentYear = new Date().getFullYear();
    expect(screen.getByDisplayValue(`CO-${currentYear}-001`)).toBeInTheDocument();
  });

  it("renders correctly in edit mode", async () => {
    render(
      <ChangeOrderModal
        open={true}
        onOk={onOk}
        onCancel={onCancel}
        confirmLoading={false}
        projectId="proj-123"
        initialValues={mockChangeOrder}
      />
    );

    await waitFor(() => {
        expect(screen.getByText("Edit Change Order")).toBeInTheDocument();
    }, { timeout: 5000 });
    
    expect(screen.getByDisplayValue("CO-2026-001")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Test Change Order")).toBeInTheDocument();
  });

  it("validates required fields on submit", async () => {
    render(
      <ChangeOrderModal
        open={true}
        onOk={onOk}
        onCancel={onCancel}
        confirmLoading={false}
        projectId="proj-123"
        existingCodes={[]}
      />
    );
    
    await waitFor(() => {
         expect(screen.getByText("Create")).toBeInTheDocument();
    }, { timeout: 5000 });

    fireEvent.click(screen.getByText("Create"));

    await waitFor(() => {
      expect(screen.getByText("Please enter a title")).toBeInTheDocument();
      expect(screen.getByText("Please enter a description")).toBeInTheDocument();
    }, { timeout: 5000 });
    
    expect(onOk).not.toHaveBeenCalled();
  });

  it("calls onOk with form values on valid submission", async () => {
    render(
      <ChangeOrderModal
        open={true}
        onOk={onOk}
        onCancel={onCancel}
        confirmLoading={false}
        projectId="proj-123"
        initialValues={mockChangeOrder}
      />
    );
    
    await waitFor(() => {
        expect(screen.getByText("Save")).toBeInTheDocument();
    }, { timeout: 5000 });

    // Change title
    const titleInput = screen.getByLabelText("Title");
    fireEvent.change(titleInput, { target: { value: "Updated Title" } });

    fireEvent.click(screen.getByText("Save"));

    await waitFor(() => {
      expect(onOk).toHaveBeenCalledWith(expect.objectContaining({
        title: "Updated Title",
        project_id: "proj-123",
      }));
    }, { timeout: 5000 });
  });
});
