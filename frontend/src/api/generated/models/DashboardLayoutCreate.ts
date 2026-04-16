/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating a new dashboard layout.
 */
export type DashboardLayoutCreate = {
    /**
     * Layout name
     */
    name: string;
    /**
     * Layout description
     */
    description?: (string | null);
    /**
     * Project scope (null = global)
     */
    project_id?: (string | null);
    /**
     * Whether this layout is a reusable template
     */
    is_template?: boolean;
    /**
     * Whether this is the user's default layout for this scope
     */
    is_default?: boolean;
    /**
     * Widget instances array
     */
    widgets?: Array<Record<string, any>>;
};

