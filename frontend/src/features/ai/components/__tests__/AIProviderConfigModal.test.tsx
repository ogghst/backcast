/**
 * Tests for AIProviderConfigModal component
 *
 * TDD Approach: RED-GREEN-REFACTOR
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "antd";
import { AIProviderConfigModal } from "../AIProviderConfigModal";
import type { AIProviderConfigPublic } from "../../types";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const API_BASE = "/api/v1";

const mockConfigs: AIProviderConfigPublic[] = [
  {
    id: "1",
    provider_id: "provider-1",
    key: "api_key",
    value: "***MASKED***",
    is_encrypted: true,
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
  {
    id: "2",
    provider_id: "provider-1",
    key: "organization",
    value: "org-123",
    is_encrypted: false,
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
];

const handlers = [
  http.get(`${API_BASE}/ai/config/providers/provider-1/configs`, () => {
    return HttpResponse.json(mockConfigs);
  }),

  http.post(`${API_BASE}/ai/config/providers/provider-1/configs/:key`, async () => {
    return HttpResponse.json({
      id: "3",
      provider_id: "provider-1",
      key: "new_key",
      value: "***MASKED***",
      is_encrypted: true,
      created_at: "2026-03-07T00:00:00Z",
      updated_at: "2026-03-07T00:00:00Z",
    });
  }),

  http.delete(`${API_BASE}/ai/config/providers/provider-1/configs/:key`, () => {
    return new HttpResponse(null, { status: 204 });
  }),
];

const server = setupServer(...handlers);

describe("AIProviderConfigModal", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    server.listen();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  afterEach(() => {
    server.resetHandlers();
  });

  afterAll(() => {
    server.close();
  });

  // Helper function to render with App wrapper for modal.confirm
  const renderWithApp = (component: React.ReactElement) => {
    return render(
      component,
      {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            <App>{children}</App>
          </QueryClientProvider>
        ),
      }
    );
  };

  const defaultProps = {
    open: true,
    onCancel: vi.fn(),
    providerId: "provider-1",
    providerName: "OpenAI",
  };

  it("should render modal with provider name in title", () => {
    renderWithApp(<AIProviderConfigModal {...defaultProps} />);

    // Modal title should be visible immediately
    expect(screen.getByText(/OpenAI/)).toBeInTheDocument();
  });

  it("should display existing configs", async () => {
    renderWithApp(<AIProviderConfigModal {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText("api_key")).toBeInTheDocument();
      expect(screen.getByText("organization")).toBeInTheDocument();
    });
  });

  it("should mask encrypted values", async () => {
    renderWithApp(<AIProviderConfigModal {...defaultProps} />);

    await waitFor(() => {
      // Encrypted value should show asterisks
      expect(screen.getByText("****")).toBeInTheDocument();
      // Non-encrypted value should show actual value
      expect(screen.getByText("org-123")).toBeInTheDocument();
    });
  });

  it("should show add config form when add button clicked", async () => {
    const user = userEvent.setup();
    renderWithApp(<AIProviderConfigModal {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText("api_key")).toBeInTheDocument();
    });

    const addButton = screen.getByText("Add Config");
    await user.click(addButton);

    expect(screen.getByLabelText("Config Key")).toBeInTheDocument();
    expect(screen.getByLabelText("Config Value")).toBeInTheDocument();
  });

  it("should use password input for config values", async () => {
    const user = userEvent.setup();
    renderWithApp(<AIProviderConfigModal {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText("api_key")).toBeInTheDocument();
    });

    const addButton = screen.getByText("Add Config");
    await user.click(addButton);

    const valueInput = screen.getByLabelText("Config Value");
    expect(valueInput).toHaveAttribute("type", "password");
  });

  it("should submit new config", async () => {
    const user = userEvent.setup();
    renderWithApp(<AIProviderConfigModal {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText("api_key")).toBeInTheDocument();
    });

    const addButton = screen.getByText("Add Config");
    await user.click(addButton);

    await user.type(screen.getByLabelText("Config Key"), "new_key");
    await user.type(screen.getByLabelText("Config Value"), "new_value");

    const submitButton = screen.getByText("Save");
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Configuration updated successfully")).toBeInTheDocument();
    });
  });

  it("should show confirmation dialog when deleting config", async () => {
    const user = userEvent.setup();
    const mockOnCancel = vi.fn();
    renderWithApp(<AIProviderConfigModal {...defaultProps} onCancel={mockOnCancel} />);

    await waitFor(() => {
      expect(screen.getByText("api_key")).toBeInTheDocument();
    });

    // Find delete button (it should be in the actions column)
    const deleteButtons = screen.getAllByLabelText("delete");
    await user.click(deleteButtons[0]);

    // Should show confirmation modal
    await waitFor(() => {
      expect(screen.getByText(/Are you sure/i)).toBeInTheDocument();
      expect(screen.getByText(/This action cannot be undone/i)).toBeInTheDocument();
    });
  });

  it("should cancel add config form", async () => {
    const user = userEvent.setup();
    renderWithApp(<AIProviderConfigModal {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText("api_key")).toBeInTheDocument();
    });

    const addButton = screen.getByText("Add Config");
    await user.click(addButton);

    await user.type(screen.getByLabelText("Config Key"), "new_key");

    const cancelButton = screen.getByText("Cancel");
    await user.click(cancelButton);

    // Form should be hidden
    expect(screen.queryByLabelText("Config Key")).not.toBeInTheDocument();
  });
});
