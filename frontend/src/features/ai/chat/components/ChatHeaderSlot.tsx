/**
 * ChatHeaderSlot
 *
 * Lightweight context that lets `ChatInterface` render its chat-specific
 * controls (AssistantSelector, New Chat, Debug toggle, sidebar/history toggle,
 * mobile overflow menu) directly inside `ChatLayout`'s slim header — using a
 * React PORTAL rather than pushing a node up via setState.
 *
 * `ChatLayout` owns the portal TARGET (a DOM node inside `ChatSlimHeader`'s
 * expanded-actions region, set once on mount). `ChatInterface` consumes that
 * target and `createPortal`s its own controls into it. Because the controls
 * remain part of `ChatInterface`'s render tree, they update normally with its
 * state, and `ChatLayout`'s only state (the target) is stable after mount — so
 * there is no setState-in-effect cycle.
 */

import { createContext, useContext } from "react";

export interface ChatHeaderSlotValue {
  /**
   * DOM node inside the slim header's expanded-actions region that
   * `ChatInterface` portals its controls into. `null` until the header mounts.
   */
  target: HTMLElement | null;
}

export const ChatHeaderSlotContext = createContext<ChatHeaderSlotValue | null>(
  null,
);

/**
 * Consume the chat header slot. Returns `null` when used outside `ChatLayout`
 * (e.g. in unit tests that render `ChatInterface` without the shell) — callers
 * must guard against that.
 */
export function useChatHeaderSlot(): ChatHeaderSlotValue | null {
  return useContext(ChatHeaderSlotContext);
}
