/**
 * useStreamingChat Permission Error Tests
 *
 * Tests for 403 permission error detection and handling in the streaming chat hook.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { WSConnectionState, type WSPermissionDeniedMessage } from "../types";
import { useStreamingChat } from "../api/useStreamingChat";

// Track WebSocket instances
interface MockWebSocketInstance {
  readyState: number;
  url: string;
  sentMessages: string[];
  eventHandlers: Record<string, EventListener[]>;
  dispatchEvent(event: Event): void;
}

let wsInstances: MockWebSocketInstance[] = [];

// Mock WebSocket class
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  url: string;
  sentMessages: string[] = [];
  eventHandlers: Record<string, EventListener[]> = {};

  constructor(url: string) {
    this.url = url;
    wsInstances.push(this as MockWebSocketInstance);

    // Simulate connection opening asynchronously
    Promise.resolve().then(() => {
      this.readyState = MockWebSocket.OPEN;
      this.dispatchEvent(new Event("open"));
    });
  }

  addEventListener(event: string, handler: EventListener) {
    if (!this.eventHandlers[event]) {
      this.eventHandlers[event] = [];
    }
    this.eventHandlers[event].push(handler);
  }

  removeEventListener(event: string, handler: EventListener) {
    if (this.eventHandlers[event]) {
      this.eventHandlers[event] = this.eventHandlers[event].filter(
        (h) => h !== handler
      );
    }
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSING;
    Promise.resolve().then(() => {
      this.readyState = MockWebSocket.CLOSED;
      this.dispatchEvent(new Event("close"));
    });
  }

  dispatchEvent(event: Event) {
    const handlers = this.eventHandlers[event.type] || [];
    handlers.forEach((handler) => handler(event));
  }
}

// Mock the global WebSocket
vi.stubGlobal("WebSocket", MockWebSocket);

// Mock the auth store
const mockUseAuthStore = vi.fn();
const mockUseTimeMachineStore = vi.fn();

type AuthStoreSelector<T> = (
  state: { token: string | null; user?: { user_id: string } }
) => T;
type TimeMachineStoreSelector<T> = (state: Record<string, unknown>) => T;

vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: <T,>(selector: AuthStoreSelector<T>) =>
    mockUseAuthStore(selector),
}));

vi.mock("@/stores/useTimeMachineStore", () => ({
  useTimeMachineStore: <T,>(selector: TimeMachineStoreSelector<T>) =>
    mockUseTimeMachineStore(selector),
}));

describe("useStreamingChat Permission Error Handling", () => {
  const mockToken = "test-jwt-token";
  const mockAssistantId = "assistant-123";
  const mockOnToken = vi.fn();
  const mockOnComplete = vi.fn();
  const mockOnError = vi.fn();

  const mockAuthState = {
    token: mockToken,
    user: {
      user_id: "user-123",
      email: "test@example.com",
    },
  };

  const mockTimeMachineState = {
    getSelectedTime: () => null,
    getSelectedBranch: () => "main",
    getViewMode: () => "merged",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    wsInstances = [];

    mockUseAuthStore.mockImplementation(
      (selector: AuthStoreSelector<unknown>) => selector(mockAuthState)
    );

    mockUseTimeMachineStore.mockImplementation(
      (selector: TimeMachineStoreSelector<unknown>) =>
        selector(mockTimeMachineState)
    );
  });

  const getLastWsInstance = () => wsInstances[wsInstances.length - 1];

  describe("403 Permission Error Detection", () => {
    it("should detect and handle 403 permission denied errors", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            projectId: "project-abc",
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      // Wait for WebSocket to connect
      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      // Simulate a 403 permission denied message
      const permissionMessage: WSPermissionDeniedMessage = {
        type: "error",
        code: 403,
        detail: "permission_denied",
        message: "You do not have access to this project",
        project_id: "project-abc",
        required_permission: "project:read",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(permissionMessage),
        } as MessageEvent);
      });

      // Verify error state
      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
        expect(result.current.error?.message).toContain("Permission denied");
        expect(result.current.connectionState).toBe(WSConnectionState.ERROR);
      });

      // Verify onError callback was called
      expect(mockOnError).toHaveBeenCalledWith(
        expect.stringContaining("Permission denied")
      );
    });

    it("should distinguish between 403 and other error codes", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      // Simulate a generic 500 error (not permission related)
      const genericError = {
        type: "error" as const,
        code: 500,
        message: "Internal server error",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(genericError),
        } as MessageEvent);
      });

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
        expect(result.current.error?.message).toContain("Error 500");
        expect(result.current.connectionState).toBe(WSConnectionState.ERROR);
      });

      expect(mockOnError).toHaveBeenCalledWith(expect.stringContaining("Error 500"));
    });
  });

  describe("formatPermissionDeniedError Helper", () => {
    it("should format complete permission denied error with all fields", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      const completeMessage: WSPermissionDeniedMessage = {
        type: "error",
        code: 403,
        detail: "permission_denied",
        message: "Access denied",
        project_id: "project-xyz",
        required_permission: "project:write",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(completeMessage),
        } as MessageEvent);
      });

      await waitFor(() => {
        expect(result.current.error?.message).toBe(
          "Permission denied: You need 'project:write' permission for project project-xyz. Access denied"
        );
      });
    });

    it("should handle permission error with only project_id", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      const projectOnlyMessage: WSPermissionDeniedMessage = {
        type: "error",
        code: 403,
        detail: "permission_denied",
        message: "Not authorized",
        project_id: "project-xyz",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(projectOnlyMessage),
        } as MessageEvent);
      });

      await waitFor(() => {
        expect(result.current.error?.message).toBe(
          "Permission denied: You do not have access to project project-xyz. Not authorized"
        );
      });
    });

    it("should handle permission error with only required_permission", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      const permissionOnlyMessage: WSPermissionDeniedMessage = {
        type: "error",
        code: 403,
        detail: "permission_denied",
        message: "Insufficient permissions",
        required_permission: "system:admin",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(permissionOnlyMessage),
        } as MessageEvent);
      });

      await waitFor(() => {
        expect(result.current.error?.message).toBe(
          "Permission denied: Required permission: system:admin. Insufficient permissions"
        );
      });
    });

    it("should handle minimal permission error with base message only", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      const minimalMessage: WSPermissionDeniedMessage = {
        type: "error",
        code: 403,
        detail: "permission_denied",
        message: "Access forbidden",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(minimalMessage),
        } as MessageEvent);
      });

      await waitFor(() => {
        expect(result.current.error?.message).toBe("Access forbidden");
      });
    });
  });

  describe("Project ID in Error Messages", () => {
    it("should include project_id in permission denied error", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      const projectErrorMessage: WSPermissionDeniedMessage = {
        type: "error",
        code: 403,
        detail: "permission_denied",
        message: "No access",
        project_id: "proj-12345",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(projectErrorMessage),
        } as MessageEvent);
      });

      await waitFor(() => {
        expect(result.current.error?.message).toContain("proj-12345");
      });

      expect(mockOnError).toHaveBeenCalledWith(expect.stringContaining("proj-12345"));
    });

    it("should format project-specific permission message correctly", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      const specificProjectMessage: WSPermissionDeniedMessage = {
        type: "error",
        code: 403,
        detail: "permission_denied",
        message: "Cannot access project",
        project_id: "project-abc-123",
        required_permission: "project:read",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(specificProjectMessage),
        } as MessageEvent);
      });

      await waitFor(() => {
        const errorMsg = result.current.error?.message;
        expect(errorMsg).toContain("project-abc-123");
        expect(errorMsg).toContain("project:read");
        expect(errorMsg).toContain("Cannot access project");
      });
    });
  });

  describe("Required Permission Display", () => {
    it("should display required_permission in error message", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      const permissionMessage: WSPermissionDeniedMessage = {
        type: "error",
        code: 403,
        detail: "permission_denied",
        message: "Permission required",
        required_permission: "project:admin",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(permissionMessage),
        } as MessageEvent);
      });

      await waitFor(() => {
        expect(result.current.error?.message).toContain("project:admin");
      });

      expect(mockOnError).toHaveBeenCalledWith(expect.stringContaining("project:admin"));
    });

    it("should show different permission types correctly", async () => {
      const permissions = [
        "project:read",
        "project:write",
        "project:admin",
        "system:admin",
        "project:members:manage",
      ];

      for (const permission of permissions) {
        // Clear previous mocks
        vi.clearAllMocks();
        wsInstances = [];

        const { result } = renderHook(
          () =>
            useStreamingChat({
              assistantId: mockAssistantId,
              onToken: mockOnToken,
              onComplete: mockOnComplete,
              onError: mockOnError,
            })
        );

        await waitFor(() => {
          expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
        });

        const permissionMessage: WSPermissionDeniedMessage = {
          type: "error",
          code: 403,
          detail: "permission_denied",
          message: "Need permission",
          required_permission: permission,
        };

        act(() => {
          const ws = getLastWsInstance();
          ws.dispatchEvent({
            type: "message",
            data: JSON.stringify(permissionMessage),
          } as MessageEvent);
        });

        await waitFor(() => {
          expect(result.current.error?.message).toContain(permission);
        });

        expect(mockOnError).toHaveBeenCalledWith(expect.stringContaining(permission));
      }
    });
  });

  describe("Project-Level vs Global Permission Denials", () => {
    it("should handle project-level permission denials", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      const projectLevelError: WSPermissionDeniedMessage = {
        type: "error",
        code: 403,
        detail: "permission_denied",
        message: "Cannot perform action on this project",
        project_id: "project-789",
        required_permission: "project:write",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(projectLevelError),
        } as MessageEvent);
      });

      await waitFor(() => {
        const errorMsg = result.current.error?.message;
        expect(errorMsg).toContain("project-789");
        expect(errorMsg).toContain("project:write");
        expect(errorMsg).toContain("Cannot perform action on this project");
      });

      // Verify connection state is set to ERROR
      expect(result.current.connectionState).toBe(WSConnectionState.ERROR);
    });

    it("should handle global permission denials", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      const globalPermissionError: WSPermissionDeniedMessage = {
        type: "error",
        code: 403,
        detail: "permission_denied",
        message: "System-level permission required",
        required_permission: "system:admin",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(globalPermissionError),
        } as MessageEvent);
      });

      await waitFor(() => {
        const errorMsg = result.current.error?.message;
        expect(errorMsg).toContain("system:admin");
        expect(errorMsg).not.toContain("project");
        expect(errorMsg).toContain("System-level permission required");
      });

      expect(result.current.connectionState).toBe(WSConnectionState.ERROR);
    });

    it("should handle permission denial without project context", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      const noProjectContextError: WSPermissionDeniedMessage = {
        type: "error",
        code: 403,
        detail: "permission_denied",
        message: "You are not authorized for this operation",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(noProjectContextError),
        } as MessageEvent);
      });

      await waitFor(() => {
        expect(result.current.error?.message).toBe("You are not authorized for this operation");
      });

      expect(result.current.connectionState).toBe(WSConnectionState.ERROR);
    });
  });

  describe("Error State and Connection Lifecycle", () => {
    it("should set connection state to ERROR on permission denied", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      // Initial state should be OPEN
      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      // Send permission denied error
      const permissionError: WSPermissionDeniedMessage = {
        type: "error",
        code: 403,
        detail: "permission_denied",
        message: "Access denied",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(permissionError),
        } as MessageEvent);
      });

      // State should change to ERROR
      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.ERROR);
      });
    });

    it("should set connection state to ERROR and prevent further message processing", async () => {
      const { result } = renderHook(
        () =>
          useStreamingChat({
            assistantId: mockAssistantId,
            onToken: mockOnToken,
            onComplete: mockOnComplete,
            onError: mockOnError,
          })
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
      });

      // Send permission denied error
      const permissionError: WSPermissionDeniedMessage = {
        type: "error",
        code: 403,
        detail: "permission_denied",
        message: "Access denied",
      };

      act(() => {
        const ws = getLastWsInstance();
        ws.dispatchEvent({
          type: "message",
          data: JSON.stringify(permissionError),
        } as MessageEvent);
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe(WSConnectionState.ERROR);
      });

      // Verify error state is set
      expect(result.current.error).toBeTruthy();
      expect(result.current.error?.message).toContain("Access denied");

      // Verify onError was called
      expect(mockOnError).toHaveBeenCalledWith(expect.stringContaining("Access denied"));
    });
  });
});
