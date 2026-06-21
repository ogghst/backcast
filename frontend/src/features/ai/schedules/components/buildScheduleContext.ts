/**
 * Build the schedule API context payload (and project_id) from the modal's
 * selector state. Extracted from the component so it can be unit-tested
 * directly and keep the component file component-only (react-refresh).
 */
import type { AgentScheduleFormValues } from "./AgentScheduleFormValues";

export function buildScheduleContext(values: AgentScheduleFormValues): {
  project_id: string | null;
  context: Record<string, unknown>;
} {
  switch (values.context_scope) {
    case "project":
      return {
        project_id: values.scope_project_id ?? null,
        context: {
          type: "project",
          id: values.scope_project_id,
          name: values.scope_project_name ?? "",
        },
      };
    case "wbe":
      return {
        project_id: values.scope_project_id ?? null,
        context: {
          type: "wbe",
          id: values.scope_wbe_id,
          project_id: values.scope_project_id,
          name: values.scope_wbe_name ?? "",
        },
      };
    case "global":
    default:
      return { project_id: null, context: { type: "general" } };
  }
}
