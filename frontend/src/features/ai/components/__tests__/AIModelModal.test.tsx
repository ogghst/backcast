/**
 * Tests for AIModelModal component
 *
 * TDD Approach: RED-GREEN-REFACTOR
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AIModelModal } from "../AIModelModal";
import type { AIModelPublic } from "../../types";

describe("AIModelModal", () => {
  const mockOnOk = vi.fn();
  const mockOnCancel = vi.fn();

  const defaultProps = {
    open: true,
    onCancel: mockOnCancel,
    onOk: mockOnOk,
    confirmLoading: false,
    providerId: "provider-1",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Create mode", () => {
    it("should render modal with create title", () => {
      render(<AIModelModal {...defaultProps} />);

      expect(screen.getByText("Create AI Model")).toBeInTheDocument();
    });

    it("should render all form fields", () => {
      render(<AIModelModal {...defaultProps} />);

      expect(screen.getByLabelText("Model ID")).toBeInTheDocument();
      expect(screen.getByLabelText("Display Name")).toBeInTheDocument();
    });

    it("should not show is_active switch in create mode", () => {
      render(<AIModelModal {...defaultProps} />);

      expect(screen.queryByLabelText("Active")).not.toBeInTheDocument();
    });

    it("should validate required fields", async () => {
      const user = userEvent.setup();
      render(<AIModelModal {...defaultProps} />);

      // Try to submit without filling form
      const submitButton = screen.getByTestId("submit-model-btn");
      await user.click(submitButton);

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/Please enter model ID/i)).toBeInTheDocument();
        expect(screen.getByText(/Please enter display name/i)).toBeInTheDocument();
      });

      // onOk should not be called
      expect(mockOnOk).not.toHaveBeenCalled();
    });

    it("should validate model_id max length", async () => {
      const user = userEvent.setup();
      render(<AIModelModal {...defaultProps} />);

      const modelIdInput = screen.getByLabelText("Model ID");
      await user.type(
        modelIdInput,
        "a".repeat(101) // Exceeds 100 char limit
      );

      const submitButton = screen.getByTestId("submit-model-btn");
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/Model ID must be 100 characters or less/i)
        ).toBeInTheDocument();
      });
    });

    it("should validate display_name max length", async () => {
      const user = userEvent.setup();
      render(<AIModelModal {...defaultProps} />);

      const displayNameInput = screen.getByLabelText("Display Name");
      await user.type(
        displayNameInput,
        "a".repeat(256) // Exceeds 255 char limit
      );

      const submitButton = screen.getByTestId("submit-model-btn");
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/Display name must be 255 characters or less/i)
        ).toBeInTheDocument();
      });
    });

    it("should submit valid data", async () => {
      const user = userEvent.setup();
      render(<AIModelModal {...defaultProps} />);

      // Fill form
      await user.type(screen.getByLabelText("Model ID"), "gpt-4");
      await user.type(screen.getByLabelText("Display Name"), "GPT-4");

      // Submit
      const submitButton = screen.getByTestId("submit-model-btn");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnOk).toHaveBeenCalledWith({
          model_id: "gpt-4",
          display_name: "GPT-4",
        });
      });
    });
  });

  describe("Edit mode", () => {
    const mockModel: AIModelPublic = {
      id: "1",
      provider_id: "provider-1",
      model_id: "gpt-4",
      display_name: "GPT-4",
      is_active: true,
      created_at: "2026-03-01T00:00:00Z",
      updated_at: "2026-03-01T00:00:00Z",
    };

    it("should render modal with edit title", () => {
      render(<AIModelModal {...defaultProps} initialValues={mockModel} />);

      expect(screen.getByText("Edit AI Model")).toBeInTheDocument();
    });

    it("should pre-fill form with initial values", () => {
      render(<AIModelModal {...defaultProps} initialValues={mockModel} />);

      expect(screen.getByLabelText("Model ID")).toHaveValue("gpt-4");
      expect(screen.getByLabelText("Display Name")).toHaveValue("GPT-4");
    });

    it("should show is_active switch in edit mode", () => {
      render(<AIModelModal {...defaultProps} initialValues={mockModel} />);

      expect(screen.getByLabelText("Active")).toBeInTheDocument();
      expect(screen.getByLabelText("Active")).toBeChecked();
    });

    it("should submit updated data", async () => {
      const user = userEvent.setup();
      render(<AIModelModal {...defaultProps} initialValues={mockModel} />);

      await user.clear(screen.getByLabelText("Display Name"));
      await user.type(screen.getByLabelText("Display Name"), "GPT-4 Turbo");

      const submitButton = screen.getByTestId("submit-model-btn");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnOk).toHaveBeenCalledWith({
          model_id: "gpt-4",
          display_name: "GPT-4 Turbo",
          is_active: true,
        });
      });
    });
  });

  describe("Modal interactions", () => {
    it("should call onCancel when cancel button clicked", async () => {
      const user = userEvent.setup();
      render(<AIModelModal {...defaultProps} />);

      const cancelButton = screen.getByText("Cancel");
      await user.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalled();
    });

    it("should reset form when reopened", async () => {
      const user = userEvent.setup();
      const { rerender } = render(
        <AIModelModal {...defaultProps} initialValues={null} />
      );

      // Fill form
      await user.type(screen.getByLabelText("Model ID"), "gpt-3.5-turbo");
      await user.type(screen.getByLabelText("Display Name"), "GPT-3.5");

      // Close and reopen
      rerender(<AIModelModal {...defaultProps} open={false} initialValues={null} />);
      rerender(<AIModelModal {...defaultProps} open={true} initialValues={null} />);

      // Form should be reset
      expect(screen.getByLabelText("Model ID")).toHaveValue("");
      expect(screen.getByLabelText("Display Name")).toHaveValue("");
    });
  });
});
