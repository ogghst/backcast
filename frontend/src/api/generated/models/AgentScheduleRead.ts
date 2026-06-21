/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading an agent schedule.
 */
export type AgentScheduleRead = {
    id: string;
    name: string;
    prompt: string;
    assistant_config_id: string;
    execution_mode: string;
    cron_expr: string;
    timezone: string;
    is_active: boolean;
    project_id: (string | null);
    branch_id: (string | null);
    context: (Record<string, any> | null);
    owner_user_id: string;
    last_run_at: (string | null);
    last_execution_id: (string | null);
    next_run_at: (string | null);
    created_at: string;
    updated_at: string;
};

