import { createContext, useContext } from "react";

export type InteractionMode = "move" | "resize";

interface ActiveInteraction {
  instanceId: string;
  mode: InteractionMode;
}

export interface WidgetInteractionContextValue {
  /** Get the current interaction mode for a specific widget instance */
  getInteraction: (instanceId: string) => InteractionMode | null;
  /** Set or toggle interaction mode for a widget instance */
  setInteraction: (instanceId: string, mode: InteractionMode) => void;
  /** Clear the active interaction */
  clearInteraction: () => void;
  /** The full active interaction (used by DashboardGrid for layout flags) */
  activeInteraction: ActiveInteraction | null;
}

export const WidgetInteractionContext =
  createContext<WidgetInteractionContextValue>({
    getInteraction: () => null,
    setInteraction: () => {},
    clearInteraction: () => {},
    activeInteraction: null,
  });

export function useWidgetInteraction(instanceId: string) {
  const ctx = useContext(WidgetInteractionContext);
  return {
    mode: ctx.getInteraction(instanceId),
    setMode: (mode: InteractionMode) =>
      ctx.setInteraction(instanceId, mode),
    clear: ctx.clearInteraction,
  };
}
