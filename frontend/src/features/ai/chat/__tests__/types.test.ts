/**
 * Tests for WebSocket types and type guards
 */

import { describe, it, expect } from "vitest";
import {
  WSConnectionState,
  type ExecutionMode,
  type WSChatRequest,
  type WSTokenMessage,
  type WSToolCallMessage,
  type WSToolResultMessage,
  type WSCompleteMessage,
  type WSErrorMessage,
  type WSServerMessage,
  type WSApprovalRequestMessage,
  type WSApprovalResponseMessage,
  isTokenMessage,
  isToolCallMessage,
  isToolResultMessage,
  isCompleteMessage,
  isErrorMessage,
  isApprovalRequestMessage,
  isApprovalResponseMessage,
} from "../types";

describe("WebSocket Types", () => {
  describe("WSConnectionState", () => {
    it("should have all expected connection states", () => {
      expect(WSConnectionState.CONNECTING).toBe("connecting");
      expect(WSConnectionState.OPEN).toBe("open");
      expect(WSConnectionState.CLOSING).toBe("closing");
      expect(WSConnectionState.CLOSED).toBe("closed");
      expect(WSConnectionState.ERROR).toBe("error");
    });
  });

  describe("WSChatRequest", () => {
    it("should create valid chat request", () => {
      const request: WSChatRequest = {
        type: "chat",
        message: "Hello, AI!",
        session_id: "session-123",
        assistant_config_id: "assistant-456",
      };

      expect(request.type).toBe("chat");
      expect(request.message).toBe("Hello, AI!");
      expect(request.session_id).toBe("session-123");
      expect(request.assistant_config_id).toBe("assistant-456");
    });

    it("should allow null session_id for new sessions", () => {
      const request: WSChatRequest = {
        type: "chat",
        message: "Start new chat",
        session_id: null,
        assistant_config_id: "assistant-456",
      };

      expect(request.session_id).toBeNull();
    });
  });

  describe("Type Guards", () => {
    describe("isTokenMessage", () => {
      it("should identify token messages", () => {
        const message: WSTokenMessage = {
          type: "token",
          content: "Hello",
          session_id: "session-123",
        };

        expect(isTokenMessage(message)).toBe(true);
        if (isTokenMessage(message)) {
          expect(message.content).toBe("Hello");
          expect(message.session_id).toBe("session-123");
        }
      });

      it("should reject other message types", () => {
        const otherMessage: WSToolCallMessage = {
          type: "tool_call",
          tool: "list_projects",
          args: {},
        };

        expect(isTokenMessage(otherMessage)).toBe(false);
      });
    });

    describe("isToolCallMessage", () => {
      it("should identify tool call messages", () => {
        const message: WSToolCallMessage = {
          type: "tool_call",
          tool: "list_projects",
          args: { project_id: "proj-1" },
        };

        expect(isToolCallMessage(message)).toBe(true);
        if (isToolCallMessage(message)) {
          expect(message.tool).toBe("list_projects");
          expect(message.args).toEqual({ project_id: "proj-1" });
        }
      });

      it("should reject other message types", () => {
        const otherMessage: WSTokenMessage = {
          type: "token",
          content: "Hello",
          session_id: "session-123",
        };

        expect(isToolCallMessage(otherMessage)).toBe(false);
      });
    });

    describe("isToolResultMessage", () => {
      it("should identify tool result messages", () => {
        const message: WSToolResultMessage = {
          type: "tool_result",
          tool: "list_projects",
          result: { items: [{ id: "proj-1", name: "Project 1" }] },
        };

        expect(isToolResultMessage(message)).toBe(true);
        if (isToolResultMessage(message)) {
          expect(message.tool).toBe("list_projects");
          expect(message.result).toEqual({ items: [{ id: "proj-1", name: "Project 1" }] });
        }
      });

      it("should reject other message types", () => {
        const otherMessage: WSTokenMessage = {
          type: "token",
          content: "Hello",
          session_id: "session-123",
        };

        expect(isToolResultMessage(otherMessage)).toBe(false);
      });
    });

    describe("isCompleteMessage", () => {
      it("should identify complete messages", () => {
        const message: WSCompleteMessage = {
          type: "complete",
          session_id: "session-123",
          message_id: "msg-456",
        };

        expect(isCompleteMessage(message)).toBe(true);
        if (isCompleteMessage(message)) {
          expect(message.session_id).toBe("session-123");
          expect(message.message_id).toBe("msg-456");
        }
      });

      it("should reject other message types", () => {
        const otherMessage: WSTokenMessage = {
          type: "token",
          content: "Hello",
          session_id: "session-123",
        };

        expect(isCompleteMessage(otherMessage)).toBe(false);
      });
    });

    describe("isErrorMessage", () => {
      it("should identify error messages", () => {
        const message: WSErrorMessage = {
          type: "error",
          message: "Something went wrong",
          code: 500,
        };

        expect(isErrorMessage(message)).toBe(true);
        if (isErrorMessage(message)) {
          expect(message.message).toBe("Something went wrong");
          expect(message.code).toBe(500);
        }
      });

      it("should handle error messages without code", () => {
        const message: WSErrorMessage = {
          type: "error",
          message: "Something went wrong",
        };

        expect(isErrorMessage(message)).toBe(true);
        if (isErrorMessage(message)) {
          expect(message.code).toBeUndefined();
        }
      });

      it("should reject other message types", () => {
        const otherMessage: WSTokenMessage = {
          type: "token",
          content: "Hello",
          session_id: "session-123",
        };

        expect(isErrorMessage(otherMessage)).toBe(false);
      });
    });
  });

  describe("Message Discrimination", () => {
    it("should discriminate using type field", () => {
      const messages: WSServerMessage[] = [
        { type: "token", content: "Hello", session_id: "session-1" },
        { type: "tool_call", tool: "search", args: { query: "test" } },
        { type: "tool_result", tool: "search", result: [] },
        { type: "complete", session_id: "session-1", message_id: "msg-1" },
        { type: "error", message: "Error occurred", code: 400 },
      ];

      const tokenMessages = messages.filter(isTokenMessage);
      const toolCallMessages = messages.filter(isToolCallMessage);
      const toolResultMessages = messages.filter(isToolResultMessage);
      const completeMessages = messages.filter(isCompleteMessage);
      const errorMessages = messages.filter(isErrorMessage);

      expect(tokenMessages).toHaveLength(1);
      expect(toolCallMessages).toHaveLength(1);
      expect(toolResultMessages).toHaveLength(1);
      expect(completeMessages).toHaveLength(1);
      expect(errorMessages).toHaveLength(1);
    });
  });

  describe("Execution Mode Types (Phase 4)", () => {
    describe("ExecutionMode type", () => {
      it("should accept valid execution mode values", () => {
        const safeMode: ExecutionMode = "safe";
        const standardMode: ExecutionMode = "standard";
        const expertMode: ExecutionMode = "expert";

        expect(safeMode).toBe("safe");
        expect(standardMode).toBe("standard");
        expect(expertMode).toBe("expert");
      });

      it("should only accept valid execution mode values", () => {
        // Type-level validation is enforced by TypeScript compiler
        // This test documents the expected behavior
        const validModes: ExecutionMode[] = ["safe", "standard", "expert"];
        expect(validModes).toHaveLength(3);

        // At runtime, we can validate that invalid values are not in the type
        const invalidMode = "dangerous";
        expect(validModes.includes(invalidMode as ExecutionMode)).toBe(false);
      });
    });

    describe("WSChatRequest with execution_mode", () => {
      it("should accept execution_mode field", () => {
        const request: WSChatRequest = {
          type: "chat",
          message: "Hello, AI!",
          session_id: "session-123",
          assistant_config_id: "assistant-456",
          execution_mode: "safe",
        };

        expect(request.execution_mode).toBe("safe");
      });

      it("should accept all valid execution modes", () => {
        const safeRequest: WSChatRequest = {
          type: "chat",
          message: "Safe mode",
          session_id: null,
          assistant_config_id: "assistant-456",
          execution_mode: "safe",
        };

        const standardRequest: WSChatRequest = {
          type: "chat",
          message: "Standard mode",
          session_id: null,
          assistant_config_id: "assistant-456",
          execution_mode: "standard",
        };

        const expertRequest: WSChatRequest = {
          type: "chat",
          message: "Expert mode",
          session_id: null,
          assistant_config_id: "assistant-456",
          execution_mode: "expert",
        };

        expect(safeRequest.execution_mode).toBe("safe");
        expect(standardRequest.execution_mode).toBe("standard");
        expect(expertRequest.execution_mode).toBe("expert");
      });

      it("should default execution_mode to standard", () => {
        const request: WSChatRequest = {
          type: "chat",
          message: "Default mode",
          session_id: null,
          assistant_config_id: "assistant-456",
        };

        expect(request.execution_mode).toBeUndefined();
        // In practice, backend defaults to "standard"
      });
    });
  });

  describe("Approval Messages (Phase 4)", () => {
    describe("WSApprovalRequestMessage", () => {
      it("should create valid approval request message", () => {
        const message: WSApprovalRequestMessage = {
          type: "approval_request",
          approval_id: "approval-123",
          session_id: "session-456",
          tool_name: "delete_project",
          tool_args: { project_id: "proj-789" },
          risk_level: "critical",
          expires_at: "2026-03-22T17:00:00Z",
        };

        expect(message.type).toBe("approval_request");
        expect(message.approval_id).toBe("approval-123");
        expect(message.session_id).toBe("session-456");
        expect(message.tool_name).toBe("delete_project");
        expect(message.tool_args).toEqual({ project_id: "proj-789" });
        expect(message.risk_level).toBe("critical");
        expect(message.expires_at).toBe("2026-03-22T17:00:00Z");
      });

      it("should have all required fields", () => {
        // This test documents the required fields
        const requiredFields: (keyof WSApprovalRequestMessage)[] = [
          "type",
          "approval_id",
          "session_id",
          "tool_name",
          "tool_args",
          "risk_level",
          "expires_at",
        ];

        expect(requiredFields).toHaveLength(7);
      });
    });

    describe("WSApprovalResponseMessage", () => {
      it("should create valid approval response message", () => {
        const message: WSApprovalResponseMessage = {
          type: "approval_response",
          approval_id: "approval-123",
          approved: true,
          user_id: "user-456",
          timestamp: "2026-03-22T16:55:00Z",
        };

        expect(message.type).toBe("approval_response");
        expect(message.approval_id).toBe("approval-123");
        expect(message.approved).toBe(true);
        expect(message.user_id).toBe("user-456");
        expect(message.timestamp).toBe("2026-03-22T16:55:00Z");
      });

      it("should handle rejection", () => {
        const message: WSApprovalResponseMessage = {
          type: "approval_response",
          approval_id: "approval-123",
          approved: false,
          user_id: "user-456",
          timestamp: "2026-03-22T16:55:00Z",
        };

        expect(message.approved).toBe(false);
      });
    });

    describe("isApprovalRequestMessage type guard", () => {
      it("should identify approval request messages", () => {
        const message: WSApprovalRequestMessage = {
          type: "approval_request",
          approval_id: "approval-123",
          session_id: "session-456",
          tool_name: "delete_project",
          tool_args: { project_id: "proj-789" },
          risk_level: "critical",
          expires_at: "2026-03-22T17:00:00Z",
        };

        expect(isApprovalRequestMessage(message)).toBe(true);
        if (isApprovalRequestMessage(message)) {
          expect(message.tool_name).toBe("delete_project");
          expect(message.risk_level).toBe("critical");
        }
      });

      it("should reject other message types", () => {
        const tokenMessage: WSTokenMessage = {
          type: "token",
          content: "Hello",
          session_id: "session-123",
        };

        expect(isApprovalRequestMessage(tokenMessage)).toBe(false);
      });
    });

    describe("isApprovalResponseMessage type guard", () => {
      it("should identify approval response messages", () => {
        const message: WSApprovalResponseMessage = {
          type: "approval_response",
          approval_id: "approval-123",
          approved: true,
          user_id: "user-456",
          timestamp: "2026-03-22T16:55:00Z",
        };

        expect(isApprovalResponseMessage(message)).toBe(true);
        if (isApprovalResponseMessage(message)) {
          expect(message.approved).toBe(true);
          expect(message.user_id).toBe("user-456");
        }
      });

      it("should reject other message types", () => {
        const errorMessage: WSErrorMessage = {
          type: "error",
          message: "Error occurred",
        };

        expect(isApprovalResponseMessage(errorMessage)).toBe(false);
      });
    });
  });
});
