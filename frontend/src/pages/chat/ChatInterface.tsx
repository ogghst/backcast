/**
 * Chat Interface Page
 *
 * User-facing page for AI chat conversations.
 * Requires 'ai-chat' permission.
 *
 * Context is derived from URL search params via `useChatContextFromUrl`
 * (the `?ctx=…` contract) and passed into `<ChatInterface>` as the required
 * `context` prop. `sessionId`/`executionId` come from the hook's `session`/
 * `exec` query riders, falling back to router `location.state` for transition
 * safety (e.g. Agents History deep links that still use state).
 */

import { useLocation } from "react-router-dom";
import { ChatInterface } from "@/features/ai/chat";
import { useChatContextFromUrl } from "@/hooks/navigation/useChatContextFromUrl";

export const ChatInterfacePage = () => {
  const location = useLocation();
  const state = location.state as
    | { sessionId?: string; executionId?: string }
    | null;

  const { context, sessionId, executionId } = useChatContextFromUrl();

  return (
    <ChatInterface
      sessionId={sessionId ?? state?.sessionId}
      executionId={executionId ?? state?.executionId}
      context={context}
    />
  );
};

export default ChatInterfacePage;
