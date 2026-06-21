/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for patching an agent schedule (all fields optional).
 */
export type AgentScheduleUpdate = {
    name?: (string | null);
    prompt?: (string | null);
    assistant_config_id?: (string | null);
    execution_mode?: ('safe' | 'standard' | 'expert' | null);
    cron_expr?: (string | null);
    timezone?: (string | null);
    is_active?: (boolean | null);
    project_id?: (string | null);
    branch_id?: (string | null);
    context?: (Record<string, any> | null);
};

