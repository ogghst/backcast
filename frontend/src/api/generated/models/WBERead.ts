/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading WBE data.
 */
export type WBERead = {
    /**
     * Parent project root ID
     */
    project_id: string;
    /**
     * WBS code (e.g., 1.2.3)
     */
    code: string;
    /**
     * WBE name
     */
    name: string;
    /**
     * Budget allocation
     */
    budget_allocation?: string;
    /**
     * Hierarchy level
     */
    level?: number;
    /**
     * Parent WBE root ID
     */
    parent_wbe_id?: (string | null);
    /**
     * Description
     */
    description?: (string | null);
    id: string;
    wbe_id: string;
    branch: string;
    created_at?: (string | null);
    created_by: string;
    created_by_name?: (string | null);
    deleted_by?: (string | null);
};

