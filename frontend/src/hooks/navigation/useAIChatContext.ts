/**
 * Context-Aware AI Chat Navigation Hook
 *
 * Detects the current AI chat context based on route parameters.
 * This allows the AI chat to automatically scope conversations
 * to the current entity (project, WBE, or cost element).
 *
 * @returns SessionContext object representing the current context
 */

import { useParams } from "react-router-dom";
import { useMemo } from "react";
import type { SessionContext } from "@/features/ai/types";

export function useAIChatContext(): SessionContext {
  const { projectId, wbsElementId, id: costElementId } = useParams();

  return useMemo(() => {
    // Cost element context (highest priority after WBE)
    if (costElementId) {
      return {
        type: "cost_element",
        id: costElementId,
        project_id: projectId,
      };
    }

    // Work Breakdown Element context
    if (wbsElementId) {
      return {
        type: "wbs_element",
        id: wbsElementId,
        project_id: projectId,
      };
    }

    // Project context
    if (projectId) {
      return {
        type: "project",
        id: projectId,
      };
    }

    // General context (no project/entity)
    return {
      type: "general",
    };
  }, [projectId, wbsElementId, costElementId]);
}
