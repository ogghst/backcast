/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to recover a stuck change order workflow.
 *
 * Context: Admin-only endpoint to recover stuck change orders when
 * impact analysis fails or workflow gets stuck in intermediate states.
 *
 * Args:
 * impact_level: Manual impact level assignment (LOW/MEDIUM/HIGH/CRITICAL)
 * assigned_approver_id: User to assign as approver
 * skip_impact_analysis: Skip impact analysis and use manual values
 * recovery_reason: Explanation for recovery (10-500 chars)
 * control_date: Optional control date for the operation (defaults to now)
 */
export type ChangeOrderRecoveryRequest = {
    /**
     * Manual impact level assignment
     */
    impact_level: string;
    /**
     * User to assign as approver (use User.id, not User.user_id)
     */
    assigned_approver_id: string;
    /**
     * Skip impact analysis and use manual values
     */
    skip_impact_analysis?: boolean;
    /**
     * Explanation for recovery (required for audit)
     */
    recovery_reason: string;
    /**
     * Control date for the workflow operation (defaults to now)
     */
    control_date?: (string | null);
};

