/**
 * Tests for WebSocket types and type guards
 */

import { describe, it, expect } from "vitest";
import {
  WSConnectionState,
  type WSChatRequest,
  type WSTokenMessage,
  type WSToolCallMessage,
  type WSToolResultMessage,
  type WSCompleteMessage,
  type WSErrorMessage,
  type WSServerMessage,
  isTokenMessage,
  isToolCallMessage,
  isToolResultMessage,
  isCompleteMessage,
  isErrorMessage,
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
});
