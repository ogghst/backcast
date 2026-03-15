/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Pending approval workload by approver.
 */
export type ApprovalWorkloadItem = {
    /**
     * User ID of the approver
     */
    approver_id: string;
    /**
     * Full name of the approver
     */
    approver_name: string;
    /**
     * Number of pending approvals
     */
    pending_count?: number;
    /**
     * Number of overdue approvals (past SLA deadline)
     */
    overdue_count?: number;
    /**
     * Average days waiting for approval
     */
    avg_days_waiting?: number;
};

