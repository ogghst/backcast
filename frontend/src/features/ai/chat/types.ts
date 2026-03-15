/**
 * WebSocket Message Types for AI Chat
 *
 * These types define the Simple JSON protocol for WebSocket communication
 * between the frontend and backend AI chat service.
 *
 * Protocol specification:
 * backend/app/api/v1/endpoints/ws/chat.py
 */

/**
 * WebSocket connection states
 */
export enum WSConnectionState {
  CONNECTING = "connecting",
  OPEN = "open",
  CLOSING = "closing",
  CLOSED = "closed",
  ERROR = "error",
}

/**
 * Client -> Server: Chat message request
 */
export interface WSChatRequest {
  type: "chat";
  message: string;
  session_id: string | null;
  assistant_config_id: string;
  title?: string; // Optional session title (for new sessions)
}

/**
 * Server -> Client: Token streaming event
 * Sent as LLM tokens are generated
 */
export interface WSTokenMessage {
  type: "token";
  content: string;
  session_id: string;
}

/**
 * Server -> Client: Tool call notification
 * Sent when the AI agent calls a tool
 */
export interface WSToolCallMessage {
  type: "tool_call";
  tool: string;
  args: Record<string, unknown>;
}

/**
 * Server -> Client: Tool result event
 * Sent after a tool execution completes
 */
export interface WSToolResultMessage {
  type: "tool_result";
  tool: string;
  result: unknown;
}

/**
 * Server -> Client: Message completion event
 * Sent when the entire response is complete
 */
export interface WSCompleteMessage {
  type: "complete";
  session_id: string;
  message_id: string;
}

/**
 * Server -> Client: Error event
 * Sent when an error occurs during processing
 */
export interface WSErrorMessage {
  type: "error";
  message: string;
  code?: number;
}

/**
 * Discriminated union of all server message types
 * Use the `type` field to discriminate between message variants
 */
export type WSServerMessage =
  | WSTokenMessage
  | WSToolCallMessage
  | WSToolResultMessage
  | WSCompleteMessage
  | WSErrorMessage;

/**
 * Type guard to check if a server message is a token message
 */
export function isTokenMessage(message: WSServerMessage): message is WSTokenMessage {
  return message.type === "token";
}

/**
 * Type guard to check if a server message is a tool call message
 */
export function isToolCallMessage(message: WSServerMessage): message is WSToolCallMessage {
  return message.type === "tool_call";
}

/**
 * Type guard to check if a server message is a tool result message
 */
export function isToolResultMessage(message: WSServerMessage): message is WSToolResultMessage {
  return message.type === "tool_result";
}

/**
 * Type guard to check if a server message is a complete message
 */
export function isCompleteMessage(message: WSServerMessage): message is WSCompleteMessage {
  return message.type === "complete";
}

/**
 * Type guard to check if a server message is an error message
 */
export function isErrorMessage(message: WSServerMessage): message is WSErrorMessage {
  return message.type === "error";
}
