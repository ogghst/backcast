/**
 * WBE-specific AI chat page component.
 *
 * Context: Scopes the AI chat session to a specific WBE context,
 * allowing the LLM to focus on WBE-level data and analysis.
 *
 * @module pages/wbes/WBEChat
 */

import { useParams } from "react-router-dom";
import { useWBE } from "@/features/wbes/api/useWBEs";
import { ChatInterface } from "@/features/ai/chat/components/ChatInterface";

/**
 * WBE-specific chat page component.
 *
 * This component:
 * 1. Extracts the wbeId from route params
 * 2. Fetches the WBE data to get context details
 * 3. Passes WBE-scoped context to ChatInterface for focused AI chat
 *
 * @example
 * ```tsx
 * // Route: /projects/:projectId/wbes/:wbeId/chat
 * <WBEChat />
 * ```
 */
export const WBEChat = () => {
  const { wbeId } = useParams<{ projectId: string; wbeId: string }>();
  const { data: wbe } = useWBE(wbeId!);

  return (
    <ChatInterface
      contextOverride={{
        type: "wbe",
        id: wbe?.wbe_id,
        project_id: wbe?.project_id,
        name: wbe?.name,
      }}
    />
  );
};
