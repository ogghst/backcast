/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for approving or rejecting a change order.
 */
export type ChangeOrderApproval = {
    /**
     * Optional comments explaining the approval/rejection decision
     */
    comments?: (string | null);
    /**
     * Control date for the workflow operation (defaults to now)
     */
    control_date?: (string | null);
};

