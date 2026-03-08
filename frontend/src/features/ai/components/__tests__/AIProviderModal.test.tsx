/**
 * Tests for AIProviderModal component
 *
 * TDD Approach: RED-GREEN-REFACTOR
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AIProviderModal } from "../AIProviderModal";
import type { AIProviderPublic } from "../../types";

describe("AIProviderModal", () => {
  const mockOnOk = vi.fn();
  const mockOnCancel = vi.fn();

  const defaultProps = {
    open: true,
    onCancel: mockOnCancel,
    onOk: mockOnOk,
    confirmLoading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Create mode", () => {
    it("should render modal with create title", () => {
      render(<AIProviderModal {...defaultProps} />);

      expect(screen.getByText("Create AI Provider")).toBeInTheDocument();
    });

    it("should render all form fields", () => {
      render(<AIProviderModal {...defaultProps} />);

      expect(screen.getByLabelText("Provider Type")).toBeInTheDocument();
      expect(screen.getByLabelText("Name")).toBeInTheDocument();
      expect(screen.getByLabelText("Base URL (Optional)")).toBeInTheDocument();
    });

    it("should not show is_active switch in create mode", () => {
      render(<AIProviderModal {...defaultProps} />);

      expect(screen.queryByLabelText("Active")).not.toBeInTheDocument();
    });

    it("should validate required fields", async () => {
      const user = userEvent.setup();
      render(<AIProviderModal {...defaultProps} />);

      // Try to submit without filling form
      const submitButton = screen.getByTestId("submit-provider-btn");
      await user.click(submitButton);

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/Please select provider type/i)).toBeInTheDocument();
        expect(screen.getByText(/Please enter name/i)).toBeInTheDocument();
      });

      // onOk should not be called
      expect(mockOnOk).not.toHaveBeenCalled();
    });

    it("should submit valid data", async () => {
      const user = userEvent.setup();
      render(<AIProviderModal {...defaultProps} />);

      // Fill form
      await user.selectOptions(screen.getByLabelText("Provider Type"), "openai");
      await user.type(screen.getByLabelText("Name"), "OpenAI Provider");
      await user.type(screen.getByLabelText("Base URL (Optional)"), "https://api.openai.com/v1");

      // Submit
      const submitButton = screen.getByTestId("submit-provider-btn");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnOk).toHaveBeenCalledWith({
          provider_type: "openai",
          name: "OpenAI Provider",
          base_url: "https://api.openai.com/v1",
        });
      });
    });

    it("should submit with optional fields empty", async () => {
      const user = userEvent.setup();
      render(<AIProviderModal {...defaultProps} />);

      await user.selectOptions(screen.getByLabelText("Provider Type"), "ollama");
      await user.type(screen.getByLabelText("Name"), "Local Ollama");

      const submitButton = screen.getByTestId("submit-provider-btn");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnOk).toHaveBeenCalledWith({
          provider_type: "ollama",
          name: "Local Ollama",
        });
      });
    });
  });

  describe("Edit mode", () => {
    const mockProvider: AIProviderPublic = {
      id: "1",
      provider_type: "openai",
      name: "OpenAI",
      base_url: "https://api.openai.com/v1",
      is_active: true,
      created_at: "2026-03-01T00:00:00Z",
      updated_at: "2026-03-01T00:00:00Z",
    };

    it("should render modal with edit title", () => {
      render(<AIProviderModal {...defaultProps} initialValues={mockProvider} />);

      expect(screen.getByText("Edit AI Provider")).toBeInTheDocument();
    });

    it("should pre-fill form with initial values", () => {
      render(<AIProviderModal {...defaultProps} initialValues={mockProvider} />);

      expect(screen.getByLabelText("Provider Type")).toHaveValue("openai");
      expect(screen.getByLabelText("Name")).toHaveValue("OpenAI");
      expect(screen.getByLabelText("Base URL (Optional)")).toHaveValue("https://api.openai.com/v1");
    });

    it("should show is_active switch in edit mode", () => {
      render(<AIProviderModal {...defaultProps} initialValues={mockProvider} />);

      expect(screen.getByLabelText("Active")).toBeInTheDocument();
      expect(screen.getByLabelText("Active")).toBeChecked();
    });

    it("should submit updated data", async () => {
      const user = userEvent.setup();
      render(<AIProviderModal {...defaultProps} initialValues={mockProvider} />);

      await user.clear(screen.getByLabelText("Name"));
      await user.type(screen.getByLabelText("Name"), "Updated OpenAI");

      const submitButton = screen.getByTestId("submit-provider-btn");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnOk).toHaveBeenCalledWith({
          provider_type: "openai",
          name: "Updated OpenAI",
          base_url: "https://api.openai.com/v1",
          is_active: true,
        });
      });
    });
  });

  describe("Modal interactions", () => {
    it("should call onCancel when cancel button clicked", async () => {
      const user = userEvent.setup();
      render(<AIProviderModal {...defaultProps} />);

      const cancelButton = screen.getByText("Cancel");
      await user.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalled();
    });

    it("should reset form when reopened with different mode", async () => {
      const user = userEvent.setup();
      const { rerender } = render(
        <AIProviderModal {...defaultProps} initialValues={null} />
      );

      // Fill form in create mode
      await user.selectOptions(screen.getByLabelText("Provider Type"), "openai");
      await user.type(screen.getByLabelText("Name"), "Test Provider");

      // Reopen in edit mode with different provider
      const mockProvider: AIProviderPublic = {
        id: "1",
        provider_type: "azure",
        name: "Azure",
        base_url: null,
        is_active: true,
        created_at: "2026-03-01T00:00:00Z",
        updated_at: "2026-03-01T00:00:00Z",
      };

      rerender(<AIProviderModal {...defaultProps} initialValues={mockProvider} />);

      // Should show edit mode values, not previous create mode values
      expect(screen.getByLabelText("Name")).toHaveValue("Azure");
    });
  });
});
