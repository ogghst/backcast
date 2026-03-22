/**
 * Tests for temporal context integration in useStreamingChat
 *
 * Test IDs from plan:
 * - T-007: Frontend sends temporal params from Time Machine store
 * - T-007b: Frontend sends defaults for current state
 *
 * RED PHASE: These tests verify that sendMessage reads from Time Machine store
 * Expected to FAIL until integration is implemented in GREEN phase
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useStreamingChat } from "../useStreamingChat";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";

// Mock the auth store
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: vi.fn(() => ({
    token: "test-token",
  })),
}));

describe("useStreamingChat - Temporal Context Integration (RED PHASE)", () => {
  beforeEach(() => {
    // Reset Time Machine store before each test
    useTimeMachineStore.getState().clearAll();
    vi.clearAllMocks();
  });

  describe("sendMessage reads from Time Machine store", () => {
    it("should include temporal params from Time Machine store (T-007)", async () => {
      // Arrange: Set up Time Machine store with temporal context
      useTimeMachineStore.getState().setCurrentProject("proj-1");
      useTimeMachineStore.getState().selectTime(new Date("2026-01-15T10:30:00Z"));
      useTimeMachineStore.getState().selectBranch("BR-001");
      useTimeMachineStore.getState().selectViewMode("isolated");

      // Mock WebSocket
      const mockWs = {
        readyState: WebSocket.OPEN,
        send: vi.fn(),
        addEventListener: vi.fn(),
        close: vi.fn(),
      };

      vi.spyOn(global, "WebSocket").mockImplementation(
        () => mockWs as unknown as WebSocket
      );

      // Act: Render hook and send message
      const onToken = vi.fn();
      const onComplete = vi.fn();
      const onError = vi.fn();

      const { result } = renderHook(() =>
        useStreamingChat({
          assistantId: "assistant-456",
          onToken,
          onComplete,
          onError,
        })
      );

      // Wait for connection to open
      await waitFor(() => {
        expect(mockWs.addEventListener).toHaveBeenCalledWith("open", expect.any(Function));
      });

      // Call the open handler to set connection state
      const openHandler = mockWs.addEventListener.mock.calls.find(
        (call) => call[0] === "open"
      )?.[1];
      if (openHandler) {
        openHandler();
      }

      // Send message
      result.current.sendMessage("Show me project data");

      // Assert: Verify WebSocket.send was called with temporal params
      expect(mockWs.send).toHaveBeenCalled();
      const sentMessage = JSON.parse(mockWs.send.mock.calls[0][0]);

      // as_of includes milliseconds from Date.toISOString()
      expect(sentMessage.as_of).toMatch(/^2026-01-15T10:30:00/);
      expect(sentMessage.branch_name).toBe("BR-001");
      expect(sentMessage.branch_mode).toBe("isolated");
    });

    it("should send defaults when Time Machine is in current state (T-007b)", async () => {
      // Arrange: Time Machine in default state (now, main, merged)
      useTimeMachineStore.getState().setCurrentProject("proj-1");
      // Don't set any temporal params - use defaults

      const mockWs = {
        readyState: WebSocket.OPEN,
        send: vi.fn(),
        addEventListener: vi.fn(),
        close: vi.fn(),
      };

      vi.spyOn(global, "WebSocket").mockImplementation(
        () => mockWs as unknown as WebSocket
      );

      // Act: Render hook and send message
      const { result } = renderHook(() =>
        useStreamingChat({
          assistantId: "assistant-456",
          onToken: vi.fn(),
          onComplete: vi.fn(),
          onError: vi.fn(),
        })
      );

      // Wait for connection and call open handler
      await waitFor(() => {
        expect(mockWs.addEventListener).toHaveBeenCalledWith("open", expect.any(Function));
      });

      const openHandler = mockWs.addEventListener.mock.calls.find(
        (call) => call[0] === "open"
      )?.[1];
      if (openHandler) {
        openHandler();
      }

      // Send message
      result.current.sendMessage("Show current data");

      // Assert: Verify defaults are sent
      expect(mockWs.send).toHaveBeenCalled();
      const sentMessage = JSON.parse(mockWs.send.mock.calls[0][0]);

      expect(sentMessage.as_of).toBeNull();
      expect(sentMessage.branch_name).toBe("main");
      expect(sentMessage.branch_mode).toBe("merged");
    });

    it("should handle missing project context gracefully", async () => {
      // Arrange: No project set in Time Machine
      // Don't call setCurrentProject

      const mockWs = {
        readyState: WebSocket.OPEN,
        send: vi.fn(),
        addEventListener: vi.fn(),
        close: vi.fn(),
      };

      vi.spyOn(global, "WebSocket").mockImplementation(
        () => mockWs as unknown as WebSocket
      );

      // Act: Render hook and send message
      const { result } = renderHook(() =>
        useStreamingChat({
          assistantId: "assistant-456",
          onToken: vi.fn(),
          onComplete: vi.fn(),
          onError: vi.fn(),
        })
      );

      // Wait for connection and call open handler
      await waitFor(() => {
        expect(mockWs.addEventListener).toHaveBeenCalledWith("open", expect.any(Function));
      });

      const openHandler = mockWs.addEventListener.mock.calls.find(
        (call) => call[0] === "open"
      )?.[1];
      if (openHandler) {
        openHandler();
      }

      // Send message
      result.current.sendMessage("Test message");

      // Assert: Verify defaults are sent when no project context
      expect(mockWs.send).toHaveBeenCalled();
      const sentMessage = JSON.parse(mockWs.send.mock.calls[0][0]);

      expect(sentMessage.as_of).toBeNull();
      expect(sentMessage.branch_name).toBe("main");
      expect(sentMessage.branch_mode).toBe("merged");
    });
  });

  describe("sendMessage includes temporal params in every message", () => {
    it("should send temporal params on multiple messages", async () => {
      // Arrange: Set temporal context
      useTimeMachineStore.getState().setCurrentProject("proj-1");
      useTimeMachineStore.getState().selectTime(new Date("2026-02-01T12:00:00Z"));
      useTimeMachineStore.getState().selectBranch("BR-003");
      useTimeMachineStore.getState().selectViewMode("merged");

      const mockWs = {
        readyState: WebSocket.OPEN,
        send: vi.fn(),
        addEventListener: vi.fn(),
        close: vi.fn(),
      };

      vi.spyOn(global, "WebSocket").mockImplementation(
        () => mockWs as unknown as WebSocket
      );

      // Act: Send multiple messages
      const { result } = renderHook(() =>
        useStreamingChat({
          assistantId: "assistant-456",
          onToken: vi.fn(),
          onComplete: vi.fn(),
          onError: vi.fn(),
        })
      );

      await waitFor(() => {
        expect(mockWs.addEventListener).toHaveBeenCalledWith("open", expect.any(Function));
      });

      const openHandler = mockWs.addEventListener.mock.calls.find(
        (call) => call[0] === "open"
      )?.[1];
      if (openHandler) {
        openHandler();
      }

      // Send first message
      result.current.sendMessage("First message");

      // Send second message
      result.current.sendMessage("Second message");

      // Assert: Both messages include temporal params
      expect(mockWs.send).toHaveBeenCalledTimes(2);

      const firstMessage = JSON.parse(mockWs.send.mock.calls[0][0]);
      const secondMessage = JSON.parse(mockWs.send.mock.calls[1][0]);

      // as_of includes milliseconds from Date.toISOString()
      expect(firstMessage.as_of).toMatch(/^2026-02-01T12:00:00/);
      expect(firstMessage.branch_name).toBe("BR-003");
      expect(firstMessage.branch_mode).toBe("merged");

      expect(secondMessage.as_of).toMatch(/^2026-02-01T12:00:00/);
      expect(secondMessage.branch_name).toBe("BR-003");
      expect(secondMessage.branch_mode).toBe("merged");
    });

    it("should update temporal params when Time Machine changes", async () => {
      // Arrange: Start with one temporal context
      useTimeMachineStore.getState().setCurrentProject("proj-1");
      useTimeMachineStore.getState().selectTime(new Date("2026-01-01T00:00:00Z"));
      useTimeMachineStore.getState().selectBranch("main");
      useTimeMachineStore.getState().selectViewMode("merged");

      const mockWs = {
        readyState: WebSocket.OPEN,
        send: vi.fn(),
        addEventListener: vi.fn(),
        close: vi.fn(),
      };

      vi.spyOn(global, "WebSocket").mockImplementation(
        () => mockWs as unknown as WebSocket
      );

      const { result } = renderHook(() =>
        useStreamingChat({
          assistantId: "assistant-456",
          onToken: vi.fn(),
          onComplete: vi.fn(),
          onError: vi.fn(),
        })
      );

      await waitFor(() => {
        expect(mockWs.addEventListener).toHaveBeenCalledWith("open", expect.any(Function));
      });

      const openHandler = mockWs.addEventListener.mock.calls.find(
        (call) => call[0] === "open"
      )?.[1];
      if (openHandler) {
        openHandler();
      }

      // Act: Send first message
      result.current.sendMessage("First message");

      // Change temporal context
      useTimeMachineStore.getState().selectTime(new Date("2026-03-01T00:00:00Z"));
      useTimeMachineStore.getState().selectBranch("BR-005");
      useTimeMachineStore.getState().selectViewMode("isolated");

      // Send second message with new context
      result.current.sendMessage("Second message");

      // Assert: Messages reflect different temporal contexts
      expect(mockWs.send).toHaveBeenCalledTimes(2);

      const firstMessage = JSON.parse(mockWs.send.mock.calls[0][0]);
      const secondMessage = JSON.parse(mockWs.send.mock.calls[1][0]);

      // First message has original context
      // as_of includes milliseconds from Date.toISOString()
      expect(firstMessage.as_of).toMatch(/^2026-01-01T00:00:00/);
      expect(firstMessage.branch_name).toBe("main");
      expect(firstMessage.branch_mode).toBe("merged");

      // Second message has updated context
      expect(secondMessage.as_of).toMatch(/^2026-03-01T00:00:00/);
      expect(secondMessage.branch_name).toBe("BR-005");
      expect(secondMessage.branch_mode).toBe("isolated");
    });
  });
});
