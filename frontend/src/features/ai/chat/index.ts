/**
 * AI Chat Feature - Barrel Exports
 */

// Components
export { ChatInterface } from "./components/ChatInterface";
export { SessionList } from "./components/SessionList";
export { MessageList } from "./components/MessageList";
export { MessageInput } from "./components/MessageInput";
export { AssistantSelector } from "./components/AssistantSelector";
export { LoadMoreButton } from "./components/LoadMoreButton";

// API Hooks
export { useChatSessions, useChatMessages, useDeleteSession } from "./api/useChatSessions";
export { useChatSessionsPaginated } from "./api/useChatSessionsPaginated";
export { useStreamingChat } from "./api/useStreamingChat";

// Types are re-exported from the parent types.ts
export type {
  AIChatRequest,
  AIChatResponse,
  AIConversationSessionPublic,
  AIConversationMessagePublic,
  AIConversationSessionPaginated,
  MessageRole,
  ChatSession,
  ChatMessage,
} from "../types";

// WebSocket types
export type {
  UseStreamingChatConfig,
  UseStreamingChatReturn,
} from "./api/useStreamingChat";
export {
  WSConnectionState,
  type WSChatRequest,
  type WSServerMessage,
  type WSTokenMessage,
  type WSToolCallMessage,
  type WSToolResultMessage,
  type WSCompleteMessage,
  type WSErrorMessage,
  isTokenMessage,
  isToolCallMessage,
  isToolResultMessage,
  isCompleteMessage,
  isErrorMessage,
} from "./types";
