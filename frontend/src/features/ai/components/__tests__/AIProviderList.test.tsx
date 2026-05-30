/**
 * Tests for AIProviderList component
 *
 * TDD Approach: RED-GREEN-REFACTOR
 */

import { describe, it, expect, beforeEach, afterEach, afterAll, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AIProviderList } from "../AIProviderList";
import type { AIProviderPublic } from "../../types";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { App } from "antd";

// Mock auth store to provide RBAC permissions needed by <Can> guards
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: vi.fn((selector: (state: Record<string, unknown>) => unknown) =>
    selector({
      token: "test-token",
      user: { id: "user-1", email: "admin@test.com", role: "admin" },
      hasPermission: () => true,
      hasAnyPermission: () => true,
      hasAllPermissions: () => true,
      hasRole: () => true,
    })
  ),
}));

const API_BASE = "/api/v1";

const mockProviders: AIProviderPublic[] = [
  {
    id: "1",
    provider_type: "openai",
    name: "OpenAI",
    base_url: "https://api.openai.com/v1",
    is_active: true,
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
  {
    id: "2",
    provider_type: "azure",
    name: "Azure OpenAI",
    base_url: null,
    is_active: false,
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
];

const handlers = [
  http.get(`${API_BASE}/ai/config/providers`, () => {
    return HttpResponse.json(mockProviders);
  }),

  http.put(`${API_BASE}/ai/config/providers/:id`, async ({ params }) => {
    return HttpResponse.json({
      ...mockProviders.find((p) => p.id === params.id),
      is_active: true,
    });
  }),

  http.delete(`${API_BASE}/ai/config/providers/:id`, () => {
    return new HttpResponse(null, { status: 204 });
  }),
];

const server = setupServer(...handlers);

describe("AIProviderList", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  beforeAll(() => {
    server.listen({ onUnhandledRequest: "warn" });
  });

  afterEach(() => {
    server.resetHandlers();
    server.restoreHandlers();
  });

  afterAll(() => {
    server.close();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <App>{children}</App>
      </MemoryRouter>
    </QueryClientProvider>
  );

  it("should render provider list", async () => {
    render(<AIProviderList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
      expect(screen.getByText("Azure OpenAI")).toBeInTheDocument();
    });
  });

  it("should display provider type badges", async () => {
    render(<AIProviderList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("openai")).toBeInTheDocument();
      expect(screen.getByText("azure")).toBeInTheDocument();
    });
  });

  it("should display base URL when available", async () => {
    render(<AIProviderList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("https://api.openai.com/v1")).toBeInTheDocument();
    });
  });

  it("should show active status with icons", async () => {
    render(<AIProviderList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
    });

    // Active providers show a check-circle icon, inactive show close-circle
    // These render as <span> with role="img" and aria-label
    const checkIcons = screen.getAllByLabelText("check-circle");
    const closeIcons = screen.getAllByLabelText("close-circle");
    expect(checkIcons.length).toBeGreaterThanOrEqual(1);
    expect(closeIcons.length).toBeGreaterThanOrEqual(1);
  });

  it("should open create modal when Add Provider button clicked", async () => {
    const user = userEvent.setup();
    render(<AIProviderList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
    });

    const addButton = screen.getByText("Add Provider");
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByText("Create AI Provider")).toBeInTheDocument();
    });
  });

  it("should open edit modal when edit button clicked", async () => {
    const user = userEvent.setup();
    render(<AIProviderList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByLabelText("edit");
    await user.click(editButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Edit AI Provider")).toBeInTheDocument();
    });
  });

  it("should show delete confirmation when delete button clicked", async () => {
    const user = userEvent.setup();
    render(<AIProviderList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByLabelText("delete");

    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getAllByText(/Are you sure/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  it("should show configuration button inside edit modal", async () => {
    const user = userEvent.setup();
    render(<AIProviderList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
    });

    // Open edit modal first
    const editButtons = screen.getAllByLabelText("edit");
    await user.click(editButtons[0]);

    // Configuration button is inside the edit modal
    await waitFor(() => {
      expect(screen.getByText("Edit AI Provider")).toBeInTheDocument();
      expect(screen.getByTestId("configuration-btn")).toBeInTheDocument();
    });
  });

  it("should show model management button inside edit modal", async () => {
    const user = userEvent.setup();
    render(<AIProviderList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
    });

    // Open edit modal first
    const editButtons = screen.getAllByLabelText("edit");
    await user.click(editButtons[0]);

    // Models button is inside the edit modal
    await waitFor(() => {
      expect(screen.getByText("Edit AI Provider")).toBeInTheDocument();
      expect(screen.getByTestId("models-btn")).toBeInTheDocument();
    });
  });
});
