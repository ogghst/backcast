/**
 * Tests for the Notifications page.
 *
 * Mocks the notifications query/mutation hooks and the router, renders the
 * page, and asserts the title + at least one notification render. In jsdom,
 * antd's Grid.useBreakpoint() returns all-false, so `isMobile` is true and
 * the card view is the default resolved mode.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { App } from "antd";
import { Notifications } from "./Notifications";
import type { NotificationResponse } from "@/features/notifications";

const useNotificationsMock = vi.fn();
const useMarkNotificationReadMock = vi.fn(() => ({
  mutate: vi.fn(),
  isPending: false,
}));
const useMarkAllNotificationsReadMock = vi.fn(() => ({
  mutate: vi.fn(),
  isPending: false,
}));

vi.mock("@/features/notifications", async () => {
  const actual =
    await vi.importActual<typeof import("@/features/notifications")>(
      "@/features/notifications",
    );
  return {
    ...actual,
    useNotifications: (...args: unknown[]) => useNotificationsMock(...args),
    useMarkNotificationRead: () => useMarkNotificationReadMock(),
    useMarkAllNotificationsRead: () => useMarkAllNotificationsReadMock(),
  };
});

const agentItem: NotificationResponse = {
  id: "n1",
  user_id: "u1",
  event_type: "agent_completed",
  title: "Agent finished",
  message: "EVM analysis done",
  resource_type: "agent_execution",
  resource_id: "exec-1",
  read_at: null,
  created_at: new Date().toISOString(),
  severity: "notice",
  actor_type: "system",
  actor_id: null,
  project_id: null,
  category: "agent",
};

const coItem: NotificationResponse = {
  id: "n2",
  user_id: "u1",
  event_type: "change_order_submitted",
  title: "Change order submitted",
  message: "CO-001 awaiting approval",
  resource_type: "change_order",
  resource_id: "co-1",
  read_at: null,
  created_at: new Date().toISOString(),
  severity: "warning",
  actor_type: "user",
  actor_id: "u2",
  project_id: "p1",
  category: "change_order",
};

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <App>
        <MemoryRouter>
          <Notifications />
        </MemoryRouter>
      </App>
    </QueryClientProvider>,
  );
}

describe("Notifications page", () => {
  beforeEach(() => {
    useNotificationsMock.mockReturnValue({
      data: { items: [agentItem, coItem], total: 2, page: 1, per_page: 20 },
      isLoading: false,
    });
  });

  it("renders the page title and notification items", async () => {
    renderPage();

    expect(
      screen.getByRole("heading", { name: "Notifications" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Agent finished")).toBeInTheDocument();
    expect(screen.getByText("Change order submitted")).toBeInTheDocument();
  });

  it("renders a mark-as-read action for unread notifications in card view", async () => {
    renderPage();

    const markReadButtons = await screen.findAllByRole("button", {
      name: "Mark as read",
    });
    expect(markReadButtons.length).toBe(2);
  });

  it("shows the empty state when there are no notifications", async () => {
    useNotificationsMock.mockReturnValue({
      data: { items: [], total: 0, page: 1, per_page: 20 },
      isLoading: false,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("No notifications")).toBeInTheDocument();
    });
  });
});
