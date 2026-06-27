/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChangeOrderStatus } from './ChangeOrderStatus';
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
    status?: (ChangeOrderStatus | null);
    /**
     * Branch name for update (defaults to current branch)
     */
    branch?: (string | null);
    /**
     * Control date for bitemporal operations
     */
    control_date?: (string | null);
    /**
     * Optional comment for status transitions (Submit, Approve, Reject, Merge)
     */
    comment?: (string | null);
    /**
     * Custom field values (CHANGE_ORDER CustomEntityTemplate)
     */
    custom_fields?: (Record<string, any> | null);
    /**
     * Bound CustomEntityTemplate root ID
     */
    custom_entity_template_root_id?: (string | null);
    /**
     * Assigned approver (None to clear)
     */
    assigned_approver_id?: (string | null);
    /**
     * SLA assigned timestamp (None to clear)
     */
    sla_assigned_at?: (string | null);
    /**
     * SLA due date (None to clear)
     */
    sla_due_date?: (string | null);
    /**
     * SLA status (None to clear)
     */
    sla_status?: (string | null);
};

