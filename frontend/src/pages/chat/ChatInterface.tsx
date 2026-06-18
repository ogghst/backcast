/**
 * Chat Interface Page
 *
 * User-facing page for AI chat conversations.
 * Requires 'ai-chat' permission.
 *
 * Reads optional `{ sessionId, executionId }` from router location state so the
 * Agents History page (and other deep links) can land the user directly on a
 * specific session / execution.
 */

import { useLocation } from "react-router-dom";
import { ChatInterface } from "@/features/ai/chat";

export const ChatInterfacePage = () => {
  const location = useLocation();
  const state = location.state as
    | { sessionId?: string; executionId?: string }
    | null;

  return (
    <ChatInterface
      sessionId={state?.sessionId}
      executionId={state?.executionId}
    />
  );
};

export default ChatInterfacePage;
