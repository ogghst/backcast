/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
/**
 * Schema for creating a new WBE.
 */
export type WBECreate = {
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
    budget_allocation?: (number | string);
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
    /**
     * Root WBE ID (internal use only for seeding)
     */
    wbe_id?: (string | null);
    /**
     * Branch name for creation (defaults to main if not specified)
     */
    branch?: string;
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
};

