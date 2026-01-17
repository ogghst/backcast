/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
/**
 * Schema for creating a new Change Order.
 */
export type ChangeOrderCreate = {
    /**
     * Business identifier (e.g., CO-2026-001)
     */
    code: string;
    /**
     * Project this change applies to
     */
    project_id: string;
    /**
     * Brief title
     */
    title: string;
    /**
     * Detailed description
     */
    description?: (string | null);
    /**
     * Business justification
     */
    justification?: (string | null);
    /**
     * When change takes effect
     */
    effective_date?: (string | null);
    /**
     * Workflow state
     */
    status?: string;
    /**
     * Control date for bitemporal operations
     */
    control_date?: (string | null);
};

