/**
 * Tests for AIProviderList component
 *
 * TDD Approach: RED-GREEN-REFACTOR
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AIProviderList } from "../AIProviderList";
import type { AIProviderPublic } from "../../types";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { App } from "antd";

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

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <App>{children}</App>
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

  it("should show active status with tag/switch", async () => {
    render(<AIProviderList />, { wrapper });

    await waitFor(() => {
      const activeSwitches = screen.getAllByRole("switch");
      expect(activeSwitches[0]).toBeChecked(); // OpenAI is active
    });
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

  it("should open config modal when configure button clicked", async () => {
    const user = userEvent.setup();
    render(<AIProviderList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
    });

    // Find configure button (should have aria-label or tooltip)
    const configureButtons = screen.getAllByRole("button").filter(
      (btn) => btn.getAttribute("aria-label") === "setting"
    );
    expect(configureButtons.length).toBeGreaterThan(0);
  });

  it("should show delete confirmation when delete button clicked", async () => {
    const user = userEvent.setup();
    render(<AIProviderList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole("button").filter(
      (btn) => btn.getAttribute("aria-label") === "delete"
    );

    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Are you sure/i)).toBeInTheDocument();
    });
  });

  it("should toggle provider active status when switch clicked", async () => {
    const user = userEvent.setup();
    render(<AIProviderList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
    });

    const activeSwitches = screen.getAllByRole("switch");
    await user.click(activeSwitches[0]);

    // Should call update mutation
    await waitFor(() => {
      expect(screen.getByText("AI provider updated successfully")).toBeInTheDocument();
    });
  });
});
