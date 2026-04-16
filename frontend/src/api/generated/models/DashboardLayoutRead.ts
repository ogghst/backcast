/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading dashboard layout data.
 */
export type DashboardLayoutRead = {
    id: string;
    name: string;
    description: (string | null);
    user_id: string;
    project_id: (string | null);
    is_template: boolean;
    is_default: boolean;
    widgets: Array<Record<string, any>>;
    created_at: string;
    updated_at: string;
};

