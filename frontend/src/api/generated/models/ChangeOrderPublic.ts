/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for Change Order API responses.
 */
export type ChangeOrderPublic = {
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
     * Root UUID identifier
     */
    change_order_id: string;
    /**
     * Version ID (primary key)
     */
    id: string;
    /**
     * User who created this version
     */
    created_by: string;
    /**
     * When this version was created (derived from transaction_time)
     */
    created_at?: (string | null);
    /**
     * User who last updated
     */
    updated_by?: (string | null);
    /**
     * When last updated
     */
    updated_at?: (string | null);
    /**
     * Branch name
     */
    branch: string;
    /**
     * Parent version ID
     */
    parent_id?: (string | null);
    /**
     * Soft delete timestamp
     */
    deleted_at?: (string | null);
    /**
     * Valid workflow status transitions from current state
     */
    available_transitions?: (Array<string> | null);
    /**
     * Whether Change Order status can be edited in current state
     */
    can_edit_status?: boolean;
    /**
     * Whether the associated branch is locked
     */
    branch_locked?: boolean;
};

