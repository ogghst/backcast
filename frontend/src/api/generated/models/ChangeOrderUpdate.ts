/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for updating a Change Order.
 *
 * All fields are optional to support partial updates.
 */
export type ChangeOrderUpdate = {
    code?: (string | null);
    title?: (string | null);
    description?: (string | null);
    justification?: (string | null);
    effective_date?: (string | null);
    status?: (string | null);
    /**
     * Branch name for update (defaults to current branch)
     */
    branch?: (string | null);
    /**
     * Control date for bitemporal operations
     */
    control_date?: (string | null);
};

