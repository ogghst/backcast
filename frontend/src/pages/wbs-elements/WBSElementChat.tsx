/**
 * WBE-specific AI chat page component.
 *
 * Context: Scopes the AI chat session to a specific WBS Element context,
 * allowing the LLM to focus on WBE-level data and analysis.
 *
 * @module pages/wbs-elements/WBSElementChat
 */

import { useParams } from "react-router-dom";
import { useWBSElement } from "@/features/wbs-elements/api/useWBSElements";
import { ChatInterface } from "@/features/ai/chat/components/ChatInterface";

/**
 * WBE-specific chat page component.
 *
 * This component:
 * 1. Extracts the wbsElementId from route params
 * 2. Fetches the WBS Element data to get context details
 * 3. Passes WBE-scoped context to ChatInterface for focused AI chat
 *
 * @example
 * ```tsx
 * // Route: /projects/:projectId/wbs-elements/:wbsElementId/chat
 * <WBSElementChat />
 * ```
 */
export const WBSElementChat = () => {
  const { wbsElementId } = useParams<{ projectId: string; wbsElementId: string }>();
  const { data: wbe } = useWBSElement(wbsElementId!);

  return (
    <ChatInterface
      contextOverride={{
        type: "wbs_element",
        id: wbe?.wbs_element_id,
        project_id: wbe?.project_id,
        name: wbe?.name,
      }}
    />
  );
};
