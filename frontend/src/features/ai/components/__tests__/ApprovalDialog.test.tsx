/**
 * Tests for ApprovalDialog component
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ApprovalDialog } from "../ApprovalDialog";
import type { WSApprovalRequestMessage } from "../../chat/types";

describe("ApprovalDialog", () => {
  const mockApprovalRequest: WSApprovalRequestMessage = {
    type: "approval_request",
    approval_id: "approval-123",
    session_id: "session-456",
    tool_name: "delete_project",
    tool_args: { project_id: "proj-789" },
    risk_level: "critical",
    expires_at: "2026-03-22T17:00:00Z",
  };

  describe("Rendering", () => {
    it("should display when open", () => {
      render(
        <ApprovalDialog
          open={true}
          approvalRequest={mockApprovalRequest}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      );

      expect(screen.getByText(/approve tool execution/i)).toBeVisible();
    });

    it("should not display when closed", () => {
      render(
        <ApprovalDialog
          open={false}
          approvalRequest={mockApprovalRequest}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      );

      expect(screen.queryByText(/approve tool execution/i)).not.toBeInTheDocument();
    });

    it("should display tool name", () => {
      render(
        <ApprovalDialog
          open={true}
          approvalRequest={mockApprovalRequest}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      );

      expect(screen.getByText("delete_project")).toBeVisible();
    });

    it("should display risk level", () => {
      render(
        <ApprovalDialog
          open={true}
          approvalRequest={mockApprovalRequest}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      );

      // The risk level is displayed as "CRITICAL" (uppercase)
      expect(screen.getByText("CRITICAL")).toBeVisible();
    });

    it("should display tool arguments", () => {
      render(
        <ApprovalDialog
          open={true}
          approvalRequest={mockApprovalRequest}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      );

      expect(screen.getByText(/proj-789/i)).toBeVisible();
    });
  });

  describe("User interactions", () => {
    it("should call onApprove when Approve button is clicked", () => {
      const handleApprove = vi.fn();
      render(
        <ApprovalDialog
          open={true}
          approvalRequest={mockApprovalRequest}
          onApprove={handleApprove}
          onReject={vi.fn()}
        />
      );

      const approveButton = screen.getByRole("button", { name: /approve/i });
      fireEvent.click(approveButton);

      expect(handleApprove).toHaveBeenCalledTimes(1);
    });

    it("should call onReject when Reject button is clicked", () => {
      const handleReject = vi.fn();
      render(
        <ApprovalDialog
          open={true}
          approvalRequest={mockApprovalRequest}
          onApprove={vi.fn()}
          onReject={handleReject}
        />
      );

      const rejectButton = screen.getByRole("button", { name: /reject/i });
      fireEvent.click(rejectButton);

      expect(handleReject).toHaveBeenCalledTimes(1);
    });

    it("should call onCancel when Cancel button is clicked", () => {
      const handleCancel = vi.fn();
      render(
        <ApprovalDialog
          open={true}
          approvalRequest={mockApprovalRequest}
          onApprove={vi.fn()}
          onReject={vi.fn()}
          onCancel={handleCancel}
        />
      );

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);

      expect(handleCancel).toHaveBeenCalledTimes(1);
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA attributes", () => {
      render(
        <ApprovalDialog
          open={true}
          approvalRequest={mockApprovalRequest}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toBeVisible();
    });
  });
});
