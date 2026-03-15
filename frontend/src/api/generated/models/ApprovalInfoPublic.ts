/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for approval information response.
 */
export type ApprovalInfoPublic = {
    /**
     * Financial impact level (LOW/MEDIUM/HIGH/CRITICAL)
     */
    impact_level?: (string | null);
    /**
     * Financial impact details (budget_delta, revenue_delta)
     */
    financial_impact?: (Record<string, any> | null);
    /**
     * Assigned approver details
     */
    assigned_approver?: (Record<string, any> | null);
    /**
     * When the approval SLA started
     */
    sla_assigned_at?: (string | null);
    /**
     * SLA deadline for approval
     */
    sla_due_date?: (string | null);
    /**
     * Current SLA tracking status (pending/approaching/overdue)
     */
    sla_status?: (string | null);
    /**
     * Number of business days remaining until SLA deadline
     */
    sla_business_days_remaining?: (number | null);
    /**
     * Whether the current user has authority to approve this change order
     */
    user_can_approve?: boolean;
    /**
     * Current user's authority level (LOW/MEDIUM/HIGH/CRITICAL)
     */
    user_authority_level?: (string | null);
};

