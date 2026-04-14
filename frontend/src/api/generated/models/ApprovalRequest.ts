/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for approving/rejecting a tool execution via REST.
 */
export type ApprovalRequest = {
    /**
     * UUID of the approval request
     */
    approval_id: string;
    /**
     * True to approve, False to reject
     */
    approved: boolean;
};

