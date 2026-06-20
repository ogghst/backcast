/**
 * Tests for NotificationBell category filtering
 *
 * Verifies the category tabs drive the query params and that items render
 * with their category tag. Uses vi.mock to stub the query hooks.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { App } from "antd";
import { NotificationBell } from "./NotificationBell";
import type { NotificationResponse } from "../api/useNotifications";

// Stub the query hooks the bell consumes.
const useUnreadNotificationCountMock = vi.fn();
const useNotificationsMock = vi.fn();
const useMarkNotificationReadMock = vi.fn(() => ({ mutate: vi.fn(), isPending: false }));
const useMarkAllNotificationsReadMock = vi.fn(() => ({ mutate: vi.fn(), isPending: false }));

vi.mock("../api/useNotifications", () => ({
  useNotifications: (a?: unknown, b?: unknown) => useNotificationsMock(a, b),
  useUnreadNotificationCount: (a?: unknown) => useUnreadNotificationCountMock(a),
  useMarkNotificationRead: () => useMarkNotificationReadMock(),
  useMarkAllNotificationsRead: () => useMarkAllNotificationsReadMock(),
}));

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

function renderBell() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <App>
        <BrowserRouter>
          <NotificationBell />
        </BrowserRouter>
      </App>
    </QueryClientProvider>,
  );
}

describe("NotificationBell category filtering", () => {
  beforeEach(() => {
    useUnreadNotificationCountMock.mockReturnValue({ data: { count: 2 } });
    useNotificationsMock.mockReturnValue({ data: undefined, isLoading: false });
  });

  it("passes category=all (undefined) by default and renders items", async () => {
    useNotificationsMock.mockReturnValue({
      data: { items: [agentItem, coItem], total: 2, page: 1, per_page: 20 },
      isLoading: false,
    });

    renderBell();

    // Open the popover.
    await userEvent.click(screen.getByRole("button", { name: "Notifications" }));

    await waitFor(() => {
      expect(useNotificationsMock).toHaveBeenCalled();
    });

    // Default call should have category undefined.
    const lastCall = useNotificationsMock.mock.calls.at(-1)![0];
    expect(lastCall.category).toBeUndefined();
    expect(await screen.findByText("Agent finished")).toBeInTheDocument();
    expect(screen.getByText("Change order submitted")).toBeInTheDocument();
  });

  it("selecting the Agents tab re-queries with category=agent", async () => {
    useNotificationsMock.mockReturnValue({
      data: { items: [agentItem], total: 1, page: 1, per_page: 20 },
      isLoading: false,
    });

    renderBell();
    await userEvent.click(screen.getByRole("button", { name: "Notifications" }));

    // Click the "Agents" segmented option.
    await userEvent.click(await screen.findByText("Agents"));

    await waitFor(() => {
      const lastCall = useNotificationsMock.mock.calls.at(-1)![0];
      expect(lastCall.category).toBe("agent");
    });
  });

  it("renders the View all footer link", async () => {
    useNotificationsMock.mockReturnValue({
      data: { items: [], total: 0, page: 1, per_page: 20 },
      isLoading: false,
    });

    renderBell();
    await userEvent.click(screen.getByRole("button", { name: "Notifications" }));
    expect(await screen.findByText("View all")).toBeInTheDocument();
  });
});
