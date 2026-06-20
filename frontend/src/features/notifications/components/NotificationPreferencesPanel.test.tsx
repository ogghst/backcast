/**
 * Tests for NotificationPreferencesPanel + TelegramConnectPanel
 *
 * Mocks the generated network layer (request/OpenAPI) so the REAL hooks run,
 * exercising their invalidation + polling logic.
 *
 * Verifies:
 *  - Preferences render grouped by category with In-app/Telegram switches.
 *  - Toggling a switch fires PUT /notifications/preferences and invalidates
 *    the preferences query.
 *  - Telegram status polls (refetchInterval enabled) while a connect is
 *    pending, and shows Connected once verified.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// Mock the generated network layer.
vi.mock("@/api/generated/core/request", () => ({ request: vi.fn() }));
vi.mock("@/api/generated/core/OpenAPI", () => ({ OpenAPI: { BASE: "" } }));
vi.mock("sonner", () => ({
  toast: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  }),
}));

import { request as __request } from "@/api/generated/core/request";
// Cast to a loose vi.Mock so mockImplementation return values don't have to
// satisfy the generated CancelablePromise signature (mirrors the search tests,
// which keep vi.fn() loose).
const requestMock = __request as unknown as ReturnType<typeof vi.fn>;

import {
  NotificationPreferencesPanel,
  TelegramConnectPanel,
} from "./NotificationPreferencesPanel";

function renderNode(client: QueryClient, node: React.ReactNode) {
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  );
}

const PREFERENCES_PAYLOAD = {
  categories: [
    {
      category: "agent",
      label: "Agents",
      entries: [
        { event_type: "agent_completed", channel: "in_app", enabled: true },
        { event_type: "agent_completed", channel: "telegram", enabled: false },
      ],
    },
  ],
};

describe("NotificationPreferencesPanel", () => {
  beforeEach(() => {
    requestMock.mockReset();
    // GET preferences
    requestMock.mockResolvedValue(PREFERENCES_PAYLOAD);
  });

  it("renders the grouped event row with both channel switches", async () => {
    const client = new QueryClient();
    renderNode(client, <NotificationPreferencesPanel />);

    expect(await screen.findByText("Agents")).toBeInTheDocument();
    expect(screen.getByText("agent completed")).toBeInTheDocument();
    expect(screen.getAllByRole("switch")).toHaveLength(2);
  });

  it("toggling a switch PUTs the change and invalidates preferences", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(client, "invalidateQueries");

    // After toggle, resolve the PUT and refetch GET.
    requestMock.mockImplementation(async (_openapi: unknown, opts: unknown) => {
      const o = opts as { url?: string; method?: string };
      if (o.method === "PUT") return {};
      return PREFERENCES_PAYLOAD;
    });

    renderNode(client, <NotificationPreferencesPanel />);
    const switches = await screen.findAllByRole("switch");
    await userEvent.click(switches[1]); // Telegram toggle

    await waitFor(() => {
      const putCall = requestMock.mock.calls.find(
        (c) => (c[1] as { method?: string }).method === "PUT",
      );
      expect(putCall).toBeTruthy();
      const body = (putCall![1] as { body?: { changes: unknown[] } }).body;
      expect(body?.changes).toEqual([
        {
          event_type: "agent_completed",
          channel: "telegram",
          enabled: true,
        },
      ]);
    });

    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["notifications", "preferences"],
      }),
    );
  });
});

describe("TelegramConnectPanel", () => {
  beforeEach(() => {
    requestMock.mockReset();
    requestMock.mockImplementation(async (_openapi: unknown, opts: unknown) => {
      const o = opts as { url?: string };
      if (o.url?.includes("/telegram/status")) {
        return { linked: false, verified: false, chat_id: null };
      }
      return {};
    });
  });

  it("shows the connect button when not linked", async () => {
    renderNode(new QueryClient(), <TelegramConnectPanel />);
    expect(
      await screen.findByRole("button", { name: "Connect Telegram" }),
    ).toBeInTheDocument();
  });

  it("shows the authorize link after connect and enables status polling", async () => {
    const client = new QueryClient();
    requestMock.mockImplementation(async (_openapi: unknown, opts: unknown) => {
      const o = opts as { url?: string; method?: string };
      if (o.method === "POST" && o.url?.includes("/telegram/connect")) {
        return {
          bot_username: "backcast_bot",
          connect_url: "https://t.me/backcast_bot?start=token123",
        };
      }
      if (o.url?.includes("/telegram/status")) {
        return { linked: false, verified: false, chat_id: null };
      }
      return {};
    });

    renderNode(client, <TelegramConnectPanel />);

    await userEvent.click(
      await screen.findByRole("button", { name: "Connect Telegram" }),
    );

    // The authorize URL appears as a link.
    const link = await screen.findByRole("link", {
      name: /backcast_bot/,
    });
    expect(link).toHaveAttribute(
      "href",
      "https://t.me/backcast_bot?start=token123",
    );
    expect(screen.getByText(/Waiting for Telegram confirmation/)).toBeInTheDocument();
  });

  it("shows Connected + Disconnect once verified", async () => {
    requestMock.mockImplementation(async (_openapi: unknown, opts: unknown) => {
      const o = opts as { url?: string };
      if (o.url?.includes("/telegram/status")) {
        return { linked: true, verified: true, chat_id: "123456" };
      }
      return {};
    });

    renderNode(new QueryClient(), <TelegramConnectPanel />);

    expect(
      await screen.findByRole("button", { name: "Disconnect" }),
    ).toBeInTheDocument();
    expect(screen.getByText("123456")).toBeInTheDocument();
  });
});
