/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for updating a dashboard layout. All fields optional.
 */
export type DashboardLayoutUpdate = {
    /**
     * Layout name
     */
    name?: (string | null);
    /**
     * Layout description
     */
    description?: (string | null);
    /**
     * Whether this layout is a reusable template
     */
    is_template?: (boolean | null);
    /**
     * Whether this is the user's default layout
     */
    is_default?: (boolean | null);
    /**
     * Widget instances array
     */
    widgets?: null;
};

