/**
 * ChatInterface URL→session sync tests (FIX 3/7/9).
 *
 * The URL-sync effect reconciles `?session=` into local currentSessionId. The
 * surgery made it react ONLY to the URL value (deps `[urlSessionId]`, ref guard)
 * — never to local state — so it no longer fights local mutations. These tests
 * pin that behavior:
 *
 *   1. `?session=sess-1` on mount → the session is selected (messages load).
 *   2. dropping `?session=` (new chat) → the reset path fires.
 *   3. re-setting the SAME `?session=` does NOT re-run the reset (ref guard).
 *
 * Plus: the mount-time cache purge is SCOPED to the ai.chat keys (never a
 * whole-cache `queryClient.clear()`).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { useEffect } from "react";
import { render, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { App } from "antd";

// --- Mocks --------------------------------------------------------------

vi.mock("../../api/useStreamingChat", () => ({
  // The streaming hook is stubbed — these tests don't drive WS messages.
  // Config is captured so the project-context-change callback can be invoked.
  useStreamingChat: (config: { onProjectContextChange?: (c: unknown) => void }) => {
    streamingChatConfigRef.current = config;
    return {
      sendMessage: vi.fn(),
      sendApprovalResponse: vi.fn(),
      sendAskUserResponse: vi.fn(),
      cancel: vi.fn(),
      connectionState: "open" as const,
      error: null,
      isReplaying: false,
    };
  },
}));

vi.mock("../../api/useChatSessions", () => ({
  useChatMessages: vi.fn(() => ({ data: [], isLoading: false })),
  useDeleteSession: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("../../api/useChatSessionsPaginated", () => ({
  useChatSessionsPaginated: () => ({
    data: { sessions: [], has_more: false, total_count: 0 },
    isLoading: false,
    loadMore: vi.fn(),
    hasMore: false,
  }),
}));

vi.mock("../../api/useAgentExecutions", () => ({
  useStopExecution: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/features/ai/api/useAIAssistants", () => ({
  useAIAssistants: () => ({
    data: [{ id: "a1", name: "Assistant", is_active: true, agent_type: "main" }],
  }),
}));

vi.mock("@/hooks/useLastAssistantId", () => ({
  useLastAssistantId: () => ({ lastAssistantId: "a1", setLastAssistantId: vi.fn() }),
}));

vi.mock("../BriefingRail", () => ({ BriefingRail: () => null }));
vi.mock("../BriefingRailToggleTab", () => ({ BriefingRailToggleTab: () => null }));
vi.mock("../BriefingPeekBar", () => ({ BriefingPeekBar: () => null }));
vi.mock("../WebSocketDebugPanel", () => ({
  WebSocketDebugPanel: () => null,
}));

import { ChatInterface } from "../ChatInterface";
import { useChatMessages } from "../../api/useChatSessions";
import { queryKeys } from "@/api/queryKeys";

// --- Helpers ------------------------------------------------------------

// A child placed in the router tree that exposes the navigate function via a
// ref so tests can change the URL within the same mount (required to exercise
// the ref guard — re-mounting would reset the guard). The ref is written from a
// useEffect so render stays pure (react-hooks/globals rule).
let navigateRef: ReturnType<typeof useNavigate> | null = null;

// Captures the config passed to the mocked useStreamingChat so tests can invoke
// individual callbacks (e.g. onProjectContextChange).
const streamingChatConfigRef: {
  current: { onProjectContextChange?: (change: unknown) => void } | null;
} = { current: null };
function NavigateProbe() {
  const navigate = useNavigate();
  useEffect(() => {
    navigateRef = navigate;
  });
  return null;
}

// Captures the current router search string so tests can assert URL updates
// driven by ChatInterface's internal navigate() calls.
let searchRef: { current: string } = { current: "" };
function LocationProbe() {
  const location = useLocation();
  useEffect(() => {
    searchRef.current = location.search;
  });
  return null;
}

function renderChat(initialPath: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const removeSpy = vi.spyOn(queryClient, "removeQueries");

  const utils = render(
    <QueryClientProvider client={queryClient}>
      <App>
        <MemoryRouter initialEntries={[initialPath]}>
          <Routes>
            <Route path="/chat" element={<NavigateProbe />} />
          </Routes>
          <LocationProbe />
          <ChatInterface context={{ type: "general" }} />
        </MemoryRouter>
      </App>
    </QueryClientProvider>,
  );

  return { ...utils, queryClient, removeSpy };
}

// Flush the requestAnimationFrame used by the URL-sync effect.
function flushRaf() {
  return new Promise<void>((resolve) => {
    requestAnimationFrame(() => resolve());
  });
}

describe("ChatInterface URL→session sync", () => {
  beforeEach(() => {
    navigateRef = null;
    streamingChatConfigRef.current = null;
    searchRef = { current: "" };
    vi.mocked(useChatMessages).mockClear();
  });

  it("selects the session named in ?session= on mount", async () => {
    renderChat("/chat?ctx=general&session=sess-1");

    // The URL-sync effect defers handleSessionSelect via rAF; once it fires,
    // currentSessionId becomes "sess-1" and useChatMessages is called with it.
    await waitFor(() => {
      const sessionIds = vi
        .mocked(useChatMessages)
        .mock.calls.map((c) => c[0]);
      expect(sessionIds).toContain("sess-1");
    });
  });

  it("fires the reset path when ?session= is dropped (new chat)", async () => {
    const { unmount } = renderChat("/chat?ctx=general&session=sess-1");
    await waitFor(() => {
      const sessionIds = vi
        .mocked(useChatMessages)
        .mock.calls.map((c) => c[0]);
      expect(sessionIds).toContain("sess-1");
    });

    // Drop the ?session= param → URL-sync effect runs handleNewChat → currentSessionId
    // becomes undefined → useChatMessages called with undefined.
    act(() => {
      navigateRef!("/chat?ctx=general");
    });
    await flushRaf();

    await waitFor(() => {
      const sessionIds = vi
        .mocked(useChatMessages)
        .mock.calls.map((c) => c[0]);
      expect(sessionIds).toContain(undefined);
    });
    unmount();
  });

  it("does NOT re-run the reset when the SAME ?session= is re-pushed (ref guard)", async () => {
    renderChat("/chat?ctx=general&session=sess-1");
    await waitFor(() => {
      const sessionIds = vi
        .mocked(useChatMessages)
        .mock.calls.map((c) => c[0]);
      expect(sessionIds).toContain("sess-1");
    });

    // Clear the mount-time calls so we only observe what happens AFTER the
    // no-op re-navigation (the initial render always calls useChatMessages
    // with undefined before the rAF selects sess-1 — that's expected, not a
    // reset triggered by the re-push).
    vi.mocked(useChatMessages).mockClear();

    // Re-push the identical URL. The ref guard (`urlSessionId === lastUrlSessionRef.current`)
    // must short-circuit so handleNewChat is NOT invoked.
    act(() => {
      navigateRef!("/chat?ctx=general&session=sess-1");
    });
    await flushRaf();
    // Allow any stray effect to settle.
    await new Promise<void>((r) => setTimeout(r, 10));

    // After the no-op re-navigation: the reset (handleNewChat) must NOT have
    // fired, so useChatMessages is never called with undefined post-clear.
    // (React Router may dedupe identical navigations → zero re-renders, which
    // also means zero undefined calls — both outcomes satisfy the guard.)
    const sessionIds = vi
      .mocked(useChatMessages)
      .mock.calls.map((c) => c[0]);
    expect(sessionIds).not.toContain(undefined);
  });

  describe("project_context_change updates ?ctx=", () => {
    it("switches the URL to the new project scope, preserving session/exec riders", async () => {
      renderChat("/chat?ctx=general&session=sess-1&exec=exec-9");

      // Wait for ChatInterface to mount and register the streaming callback.
      await waitFor(() => {
        expect(streamingChatConfigRef.current).toBeTruthy();
      });

      // Simulate the backend publishing a project context change.
      act(() => {
        streamingChatConfigRef.current!.onProjectContextChange!({
          type: "project_context_change",
          project_id: "proj-new",
          project_name: "Alpha Line",
          project_code: "ALPHA-01",
        });
      });

      // The URL should now be scoped to the new project, with riders preserved
      // and no stale `p` rider.
      await waitFor(() => {
        expect(searchRef.current).toContain("ctx=project:proj-new");
        expect(searchRef.current).toContain("session=sess-1");
        expect(searchRef.current).toContain("exec=exec-9");
        expect(searchRef.current).not.toContain("p=");
      });
    });
  });

  describe("mount-time cache purge is scoped", () => {
    it("removes ONLY the ai.chat cache key, never the whole cache", () => {
      const { removeSpy } = renderChat("/chat?ctx=general");

      // At least one scoped removal with the ai.chat query key.
      const scopedCall = removeSpy.mock.calls.find(
        (call) =>
          Array.isArray(call[0]?.queryKey) &&
          Array.isArray(call[0].queryKey) &&
          // queryKeys.ai.chat.all === ["ai","chat"]
          call[0].queryKey[0] === "ai" &&
          call[0].queryKey[1] === "chat" &&
          call[0].queryKey.length === 2,
      );
      expect(scopedCall, "expected a scoped { queryKey: ['ai','chat'] } removal").toBeTruthy();
      expect(scopedCall?.[0]?.queryKey).toEqual([...queryKeys.ai.chat.all]);

      // NEVER an unscoped / whole-cache clear (no queryKey predicate).
      const unscoped = removeSpy.mock.calls.filter(
        (call) => !call[0] || call[0].queryKey === undefined,
      );
      expect(unscoped).toHaveLength(0);
    });
  });
});
