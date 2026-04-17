/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties returned to client.
 */
export type ProjectBudgetSettingsRead = {
    /**
     * Warning threshold percentage (0-100)
     */
    warning_threshold_percent?: string;
    /**
     * Whether project admins can override budget warnings
     */
    allow_project_admin_override?: boolean;
    /**
     * Whether to block cost registrations that exceed budget
     */
    enforce_budget?: boolean;
    id: string;
    project_budget_settings_id: string;
    project_id: string;
    created_by: string;
};

