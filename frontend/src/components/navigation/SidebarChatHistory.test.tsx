import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "antd";

// --- Mocks --------------------------------------------------------------

const mockNavigate = vi.fn();
let mockLocation = { pathname: "/projects/p1", search: "" };
let mockCtx: {
  type: "general" | "project" | "wbe" | "cost_element" | "work_package";
  id?: string;
  project_id?: string;
} = { type: "general" };
let mockSessionId: string | undefined;

vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => mockLocation,
}));

vi.mock("@/hooks/navigation/useEffectiveChatContext", () => ({
  useEffectiveChatContext: () => mockCtx,
}));

vi.mock("@/hooks/navigation/useChatContextFromUrl", async () => {
  const actual = await vi.importActual<
    typeof import("@/hooks/navigation/useChatContextFromUrl")
  >("@/hooks/navigation/useChatContextFromUrl");
  return {
    ...actual, // keep the REAL serializeCtx (its behavior is under test below)
    useChatContextFromUrl: () => ({
      context: mockCtx,
      sessionId: mockSessionId,
    }),
  };
});

const mockMutate = vi.fn();
vi.mock("@/features/ai/chat/api/useChatSessions", () => ({
  useDeleteSession: () => ({ mutate: mockMutate, isPending: false }),
}));

let mockSessionsData:
  | { sessions: Array<{ id: string; title: string; updated_at: string }> }
  | undefined = {
  sessions: [{ id: "sess-1", title: "First chat", updated_at: "2026-06-01T00:00:00Z" }],
};
let mockHasMore = false;

vi.mock("@/features/ai/chat/api/useChatSessionsPaginated", () => ({
  useChatSessionsPaginated: () => ({
    data: mockSessionsData,
    isLoading: false,
    loadMore: vi.fn(),
    hasMore: mockHasMore,
  }),
}));

import SidebarChatHistory from "./SidebarChatHistory";
import { serializeCtx } from "@/hooks/navigation/useChatContextFromUrl";

function resetState() {
  mockNavigate.mockClear();
  mockMutate.mockClear();
  mockLocation = { pathname: "/projects/p1", search: "" };
  mockCtx = { type: "general" };
  mockSessionId = undefined;
  mockSessionsData = {
    sessions: [{ id: "sess-1", title: "First chat", updated_at: "2026-06-01T00:00:00Z" }],
  };
  mockHasMore = false;
}

function renderIt() {
  return render(
    <App>
      <SidebarChatHistory />
    </App>,
  );
}

describe("serializeCtx", () => {
  it("general → 'ctx=general'", () => {
    expect(serializeCtx({ type: "general" })).toBe("ctx=general");
  });

  it("project → 'ctx=project:<id>' with NO &p (self-referential)", () => {
    expect(serializeCtx({ type: "project", id: "p1", project_id: "p1" })).toBe(
      "ctx=project:p1",
    );
  });

  it("wbe → 'ctx=wbe:<id>&p=<project_id>'", () => {
    expect(
      serializeCtx({ type: "wbe", id: "w1", project_id: "p1" }),
    ).toBe("ctx=wbe:w1&p=p1");
  });

  it("work_package → 'ctx=work_package:<id>&p=<project_id>'", () => {
    expect(
      serializeCtx({ type: "work_package", id: "wp1", project_id: "p1" }),
    ).toBe("ctx=work_package:wp1&p=p1");
  });

  it("cost_element with project_id → includes &p", () => {
    expect(
      serializeCtx({ type: "cost_element", id: "c1", project_id: "p1" }),
    ).toBe("ctx=cost_element:c1&p=p1");
  });

  it("typed context without project_id → no &p", () => {
    expect(serializeCtx({ type: "cost_element", id: "c1" })).toBe(
      "ctx=cost_element:c1",
    );
  });
});

describe("SidebarChatHistory", () => {
  beforeEach(resetState);

  it("onSessionSelect navigates to /chat?ctx=…&session=<id> with returnTo state", async () => {
    const user = userEvent.setup();
    mockLocation = { pathname: "/projects/p1", search: "?x=1" };
    mockCtx = { type: "project", id: "p1", project_id: "p1" };

    renderIt();

    const item = await screen.findByText("First chat");
    await user.click(item);

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledTimes(1));
    const [path, opts] = mockNavigate.mock.calls[0];
    expect(path).toBe("/chat?ctx=project:p1&session=sess-1");
    expect(opts.state).toEqual({ returnTo: "/projects/p1?x=1" });
  });

  it("onSessionSelect uses the wbe ctx serialization (with &p)", async () => {
    const user = userEvent.setup();
    mockLocation = { pathname: "/projects/p1/wbs-elements/w1", search: "" };
    mockCtx = { type: "wbe", id: "w1", project_id: "p1" };

    renderIt();

    const item = await screen.findByText("First chat");
    await user.click(item);

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledTimes(1));
    const [path] = mockNavigate.mock.calls[0];
    expect(path).toBe("/chat?ctx=wbe:w1&p=p1&session=sess-1");
  });

  it("onDeleteSession calls the reused delete mutation", async () => {
    const user = userEvent.setup();
    mockCtx = { type: "general" };

    const { container } = renderIt();

    // The delete trigger is an icon-only button; target it via the SessionList
    // `.delete-btn` class, then confirm the Popconfirm's OK button. The OK
    // button lives in `.ant-popconfirm-buttons` and carries the primary+danger
    // classes, so we scope to that container (the icon's aria-label also makes
    // the trigger match "delete", so a plain role+name query is ambiguous).
    await screen.findByText("First chat");
    const deleteBtn = container.querySelector(
      ".delete-btn",
    ) as HTMLButtonElement;
    expect(deleteBtn).toBeTruthy();
    await user.click(deleteBtn);

    const okBtn = await waitFor(() => {
      // The Popconfirm portal mounts in document.body, outside `container`.
      const btn = document.body.querySelector(
        ".ant-popconfirm-buttons .ant-btn-primary",
      ) as HTMLButtonElement | null;
      if (!btn) throw new Error("popconfirm OK not rendered");
      return btn;
    });
    await user.click(okBtn);

    await waitFor(() => expect(mockMutate).toHaveBeenCalledWith("sess-1"));
  });
});
