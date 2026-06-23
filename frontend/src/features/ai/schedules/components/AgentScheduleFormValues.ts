import type { AgentScheduleCreate } from "@/api/generated";

export type ContextScope = "global" | "project" | "wbe";

export interface AgentScheduleFormValues {
  name: string;
  prompt: string;
  assistant_config_id: string;
  execution_mode: NonNullable<AgentScheduleCreate["execution_mode"]>;
  cron_expr: string;
  timezone: string;
  is_active: boolean;
  context_scope: ContextScope;
  scope_project_id?: string;
  scope_project_name?: string;
  scope_wbe_id?: string;
  scope_wbe_name?: string;
}
