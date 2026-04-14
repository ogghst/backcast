/**
 * WebSocket Message Types for AI Chat
 *
 * These types define the Simple JSON protocol for WebSocket communication
 * between the frontend and backend AI chat service.
 *
 * Protocol specification:
 * backend/app/api/v1/endpoints/ws/chat.py
 */

import type { SessionContext } from "../types";

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
 * Represents a single subagent's streaming state
 */
export interface SubagentStream {
  invocation_id: string; // Unique identifier for this invocation
  subagent_name: string; // Display name (e.g., "EVM Analyst")
  content: string; // Accumulated streaming content
  is_active: boolean; // Whether this subagent is currently streaming
  is_complete: boolean; // Whether this subagent has finished
  started_at: number; // Timestamp when streaming started
  invocation_number?: number; // Invocation count for this subagent name (e.g., 2 for second invocation)
  sequence?: number; // Order in which this stream was created (for proper rendering)
}

/**
 * Represents a single main agent stream segment
 * Used to separate main agent content before/after subagent calls
 */
export interface MainAgentStream {
  invocation_id: string; // Unique identifier for this stream segment
  content: string; // Accumulated streaming content
  is_active: boolean; // Whether this stream is currently streaming
  is_complete: boolean; // Whether this stream has finished
  started_at: number; // Timestamp when streaming started
  sequence?: number; // Order in which this stream was created (for proper rendering)
}

/**
 * State for tracking multiple concurrent subagent streams
 */
export interface StreamingState {
  main: string; // Main agent content (fallback for backward compatibility)
  mainStreams: Map<string, MainAgentStream>; // invocation_id -> MainAgentStream
  subagents: Map<string, SubagentStream>; // invocation_id -> SubagentStream
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
 * Client -> Server: Subscribe to execution progress
 * Sent when reconnecting to resume receiving events for an active execution
 */
export interface WSSubscribeMessage {
  type: "subscribe";
  execution_id: string;
  last_seen_sequence: number;
}

/**
 * Server -> Client: Execution started notification
 * Sent immediately after an agent execution is created, before streaming begins
 */
export interface WSExecutionStartedMessage {
  type: "execution_started";
  execution_id: string;
}

/**
 * Server -> Client: Execution status update
 * Sent when an agent execution changes status (running, completed, error, awaiting_approval)
 */
export interface WSExecutionStatusMessage {
  type: "execution_status";
  execution_id: string;
  status: string;
  session_id: string;
}

/**
 * File attachment metadata for chat messages
 */
export interface FileAttachment {
  file_id: string; // Unique file identifier
  filename: string; // Original filename
  file_type: string; // MIME type or file extension
  file_size: number; // File size in bytes
  content?: string; // Inline content (base64 for images, extracted text for documents)
  uploaded_at: string; // Upload timestamp (ISO datetime)
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
  // Execution mode for tool risk management (required)
  execution_mode: ExecutionMode; // AI tool execution mode (safe/standard/expert)
  // Temporal context parameters for AI tools
  as_of?: string | null; // ISO timestamp or null for "now"
  branch_name?: string; // Branch name (e.g., "main", "BR-001")
  branch_mode?: "merged" | "isolated"; // Branch view mode
  // Project context for project-specific chat
  project_id?: string; // Project ID to scope chat to a specific project
  // Session context for scoping conversations (general, project, wbe, cost_element)
  context?: SessionContext; // Session context (type, id, project_id, name)
  // File attachments for the message
  attachments?: FileAttachment[]; // Document/file attachments
  images?: string[]; // Image URLs (simplified format for images)
}

/**
 * Server -> Client: Token streaming event
 * Sent as LLM tokens are generated
 */
export interface WSTokenMessage {
  type: "token";
  content: string;
  session_id: string;
  source?: "main" | "subagent";
  subagent_name?: string;
  invocation_id?: string;
}

/**
 * Server -> Client: Batched token streaming message
 * Multiple tokens sent in a single WebSocket message to reduce overhead
 */
export interface WSTokenBatchMessage {
  type: "token_batch";
  tokens: string; // Concatenated token string
  session_id: string;
  source: "main" | "subagent";
  subagent_name?: string;
  invocation_id?: string;
}

/**
 * Server -> Client: Tool call notification
 * Sent when the AI agent calls a tool
 */
export interface WSToolCallMessage {
  type: "tool_call";
  tool: string;
  args: Record<string, unknown>;
  step_number?: number;
  total_steps?: number;
  invocation_id?: string;
}

/**
 * Server -> Client: Tool result event
 * Sent after a tool execution completes
 */
export interface WSToolResultMessage {
  type: "tool_result";
  tool: string;
  result: unknown;
  invocation_id?: string;
}

/**
 * Token usage metrics reported on message completion
 */
export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

/**
 * Server -> Client: Message completion event
 * Sent when the entire response is complete
 */
export interface WSCompleteMessage {
  type: "complete";
  session_id: string;
  message_id: string;
  token_usage?: TokenUsage;
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
  step_number?: number;
  total_steps?: number;
  invocation_id?: string;
}

/**
 * Server -> Client: Subagent delegation event
 * Sent when the Deep Agent delegates to a subagent
 */
export interface WSSubagentMessage {
  type: "subagent";
  subagent: string; // Subagent name (e.g., "evm_analyst")
  message?: string; // Optional description of what the subagent is doing
  invocation_id: string; // Unique invocation ID for this subagent instance
  step_number?: number;
  total_steps?: number;
}

/**
 * Server -> Client: Agent thinking event
 * Sent when the agent is processing before first response
 */
export interface WSThinkingMessage {
  type: "thinking";
}

/**
 * Server -> Client: Subagent result event
 * Sent when a subagent (task tool) completes with its final response
 */
export interface WSSubagentResultMessage {
  type: "subagent_result";
  subagent_name: string;
  content: string;
  invocation_id: string; // Unique invocation ID for this subagent instance
}

/**
 * Server -> Client: Agent completion event
 * Sent when an agent (main or subagent) stream completes for visual purposes
 */
export interface WSAgentCompleteMessage {
  type: "agent_complete";
  agent_type: "main" | "subagent";
  invocation_id: string;
  agent_name?: string; // Agent name for display
  completed_at: string; // ISO datetime timestamp
}

/**
 * Server -> Client: Content reset event
 * Sent when the streaming content buffer should be reset,
 * typically after a subagent completes
 */
export interface WSContentResetMessage {
  type: "content_reset";
  reason: string;
}

/**
 * Server -> Client: Polling heartbeat event
 * Sent every 5 seconds during the 30-second approval polling period
 * to keep the WebSocket connection alive
 */
export interface WSPollingHeartbeatMessage {
  type: "polling_heartbeat";
  approval_id: string;
  elapsed_seconds: number;
  remaining_seconds: number;
}

/**
 * Server -> Client: Ping keepalive event
 * Sent every 20 seconds during long agent execution to prevent proxy timeouts
 */
export interface WSPingMessage {
  type: "ping";
}

/**
 * Discriminated union of all server message types
 * Use the `type` field to discriminate between message variants
 */
export type WSServerMessage =
  | WSTokenMessage
  | WSTokenBatchMessage
  | WSToolCallMessage
  | WSToolResultMessage
  | WSCompleteMessage
  | WSErrorMessage
  | WSPlanningMessage
  | WSSubagentMessage
  | WSSubagentResultMessage
  | WSThinkingMessage
  | WSContentResetMessage
  | WSPollingHeartbeatMessage
  | WSPingMessage
  | WSAgentCompleteMessage
  | WSExecutionStartedMessage
  | WSExecutionStatusMessage;

/**
 * Type guard to check if a server message is a token message.
 *
 * Context: Used by handleMessage in useStreamingChat to route streaming tokens.
 * Validates content field to prevent malformed token events from reaching the UI.
 *
 * @param message - Raw server message to validate
 * @returns True if message is a well-formed WSTokenMessage
 */
export function isTokenMessage(message: unknown): message is WSTokenMessage {
  if (typeof message !== "object" || message === null) return false;
  const msg = message as Record<string, unknown>;
  return (
    msg.type === "token" &&
    typeof msg.content === "string"
  );
}

/**
 * Type guard to check if a server message is a batched token message
 */
export function isTokenBatchMessage(message: WSServerMessage): message is WSTokenBatchMessage {
  return message.type === "token_batch";
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
 * Type guard to check if a server message is a complete message.
 *
 * Context: Used by handleMessage to detect session completion and trigger
 * query invalidation. Validates session_id to ensure cache keys are correct.
 *
 * @param message - Raw server message to validate
 * @returns True if message is a well-formed WSCompleteMessage
 */
export function isCompleteMessage(message: unknown): message is WSCompleteMessage {
  if (typeof message !== "object" || message === null) return false;
  const msg = message as Record<string, unknown>;
  return (
    msg.type === "complete" &&
    typeof msg.session_id === "string"
  );
}

/**
 * Type guard to check if a server message is an error message.
 *
 * Context: Used by handleMessage to surface errors to the user and update
 * connection state. Validates message field so error display always has text.
 *
 * @param message - Raw server message to validate
 * @returns True if message is a well-formed WSErrorMessage
 */
export function isErrorMessage(message: unknown): message is WSErrorMessage {
  if (typeof message !== "object" || message === null) return false;
  const msg = message as Record<string, unknown>;
  return (
    msg.type === "error" &&
    typeof msg.message === "string"
  );
}

/**
 * Type guard to check if a server message is a permission denied error.
 *
 * Context: Narrowing helper used after isErrorMessage to detect 403 errors
 * and show project-specific permission messages.
 *
 * @param message - Raw server message to validate
 * @returns True if message is a well-formed WSPermissionDeniedMessage
 */
export function isPermissionDeniedMessage(
  message: unknown
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
 * Type guard to check if a server message is an approval request.
 *
 * Context: Used by handleMessage to detect critical tool approval requests
 * from the interrupt node. Validates approval_id and tool_name to ensure
 * the approval dialog can render correctly.
 *
 * @param message - Raw server message to validate
 * @returns True if message is a well-formed WSApprovalRequestMessage
 */
export function isApprovalRequestMessage(
  message: unknown
): message is WSApprovalRequestMessage {
  if (typeof message !== "object" || message === null) return false;
  const msg = message as Record<string, unknown>;
  return (
    msg.type === "approval_request" &&
    typeof msg.approval_id === "string" &&
    typeof msg.tool_name === "string"
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

/**
 * Type guard to check if a server message is a subagent result message
 */
export function isSubagentResultMessage(
  message: WSServerMessage
): message is WSSubagentResultMessage {
  return message.type === "subagent_result";
}

/**
 * Type guard to check if a server message is a polling heartbeat message
 */
export function isPollingHeartbeatMessage(
  message: WSServerMessage
): message is WSPollingHeartbeatMessage {
  return message.type === "polling_heartbeat";
}

/**
 * Type guard to check if a server message is a content reset message
 */
export function isContentResetMessage(
  message: WSServerMessage
): message is WSContentResetMessage {
  return message.type === "content_reset";
}

/**
 * Type guard to check if a server message is an agent complete message
 */
export function isAgentCompleteMessage(
  message: WSServerMessage
): message is WSAgentCompleteMessage {
  return message.type === "agent_complete";
}
