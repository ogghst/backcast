/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating an agent schedule.
 */
export type AgentScheduleCreate = {
    name: string;
    prompt: string;
    assistant_config_id: string;
    execution_mode?: 'safe' | 'standard' | 'expert';
    cron_expr: string;
    timezone?: string;
    is_active?: boolean;
    project_id?: (string | null);
    branch_id?: (string | null);
    context?: (Record<string, any> | null);
};

