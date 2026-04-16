/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties for creating/updating Project Budget Settings.
 */
export type ProjectBudgetSettingsCreate = {
    /**
     * Warning threshold percentage (0-100)
     */
    warning_threshold_percent?: (number | string);
    /**
     * Whether project admins can override budget warnings
     */
    allow_project_admin_override?: boolean;
};

