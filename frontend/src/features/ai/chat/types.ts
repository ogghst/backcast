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
 * Project role definitions for RBAC
 */
export enum ProjectRole {
  PROJECT_ADMIN = "PROJECT_ADMIN",
  PROJECT_MANAGER = "PROJECT_MANAGER",
  PROJECT_EDITOR = "PROJECT_EDITOR",
  PROJECT_VIEWER = "PROJECT_VIEWER",
}

/**
 * AI tool execution modes
 * - safe: Only low-risk tools allowed
 * - standard: Low and high-risk tools allowed, critical tools require approval
 * - expert: All tools allowed without approval
 */
export type ExecutionMode = "safe" | "standard" | "expert";

/**
 * Client -> Server: Chat message request
 */
export interface WSChatRequest {
  type: "chat";
  message: string;
  session_id: string | null;
  assistant_config_id: string;
  title?: string; // Optional session title (for new sessions)
  // Execution mode for tool risk management (required)
  execution_mode: ExecutionMode; // AI tool execution mode (safe/standard/expert)
  // Temporal context parameters for AI tools
  as_of?: string | null; // ISO timestamp or null for "now"
  branch_name?: string; // Branch name (e.g., "main", "BR-001")
  branch_mode?: "merged" | "isolated"; // Branch view mode
  // Project context for project-specific chat
  project_id?: string; // Project ID to scope chat to a specific project
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
 * Server -> Client: Permission denied error (403)
 * Sent when user lacks required project-level permissions
 */
export interface WSPermissionDeniedMessage extends WSErrorMessage {
  type: "error";
  message: string;
  code: 403;
  detail: "permission_denied";
  project_id?: string;
  required_permission?: string;
}

/**
 * Server -> Client: Agent planning event
 * Sent when the Deep Agent is creating a plan (using write_todos)
 */
export interface WSPlanningMessage {
  type: "planning";
  plan?: string; // The plan description
  steps?: Array<{ text: string; done: boolean }>; // Planning steps
}

/**
 * Server -> Client: Subagent delegation event
 * Sent when the Deep Agent delegates to a subagent
 */
export interface WSSubagentMessage {
  type: "subagent";
  subagent: string; // Subagent name (e.g., "evm_analyst")
  message?: string; // Optional description of what the subagent is doing
}

/**
 * Server -> Client: Agent thinking event
 * Sent when the agent is processing before first response
 */
export interface WSThinkingMessage {
  type: "thinking";
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
  | WSErrorMessage
  | WSPlanningMessage
  | WSSubagentMessage
  | WSThinkingMessage;

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

/**
 * Type guard to check if a server message is a permission denied error
 */
export function isPermissionDeniedMessage(
  message: WSServerMessage
): message is WSPermissionDeniedMessage {
  return isErrorMessage(message) && message.code === 403;
}

/**
 * Server -> Client: Request approval for critical tool execution
 * Sent when a critical tool is about to be executed in standard mode
 */
export interface WSApprovalRequestMessage {
  type: "approval_request";
  approval_id: string; // UUID for this approval request
  session_id: string; // Chat session ID
  tool_name: string; // Name of the tool being called
  tool_args: Record<string, unknown>; // Arguments passed to the tool
  risk_level: "critical"; // Always "critical" for approval requests
  expires_at: string; // ISO datetime when approval expires (5 minutes)
}

/**
 * Client -> Server: User decision on approval request
 * Sent when user approves or rejects a critical tool execution
 */
export interface WSApprovalResponseMessage {
  type: "approval_response";
  approval_id: string; // UUID matching the approval request
  approved: boolean; // User's decision (true = approve, false = reject)
  user_id: string; // ID of the user making the decision
  timestamp: string; // ISO datetime of the decision
}

/**
 * Type guard to check if a server message is an approval request
 */
export function isApprovalRequestMessage(
  message: unknown
): message is WSApprovalRequestMessage {
  return (
    typeof message === "object" &&
    message !== null &&
    (message as Record<string, unknown>).type === "approval_request"
  );
}

/**
 * Type guard to check if a client message is an approval response
 */
export function isApprovalResponseMessage(
  message: unknown
): message is WSApprovalResponseMessage {
  return (
    typeof message === "object" &&
    message !== null &&
    (message as Record<string, unknown>).type === "approval_response"
  );
}

/**
 * Type guard to check if a server message is a planning message
 */
export function isPlanningMessage(message: WSServerMessage): message is WSPlanningMessage {
  return message.type === "planning";
}

/**
 * Type guard to check if a server message is a subagent delegation message
 */
export function isSubagentMessage(message: WSServerMessage): message is WSSubagentMessage {
  return message.type === "subagent";
}

/**
 * Type guard to check if a server message is a thinking message
 */
export function isThinkingMessage(message: WSServerMessage): message is WSThinkingMessage {
  return message.type === "thinking";
}
