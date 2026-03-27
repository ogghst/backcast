/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChangeOrderStatus } from './ChangeOrderStatus';
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
    status?: ChangeOrderStatus;
    /**
     * Financial impact level (LOW/MEDIUM/HIGH/CRITICAL)
     */
    impact_level?: (string | null);
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
     * Change branch name for impact analysis (e.g., BR-CO-2026-001)
     */
    branch_name?: (string | null);
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
    /**
     * User ID assigned to approve this change order
     */
    assigned_approver_id?: (string | null);
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
     * Assigned approver details (user_id, full_name, email, role)
     */
    assigned_approver?: (Record<string, any> | null);
};

