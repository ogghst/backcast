/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChangeOrderStatus } from './ChangeOrderStatus';
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
    status?: ChangeOrderStatus;
    /**
     * Financial impact level
     */
    impact_level?: (string | null);
    /**
     * Bound CustomEntityTemplate root ID
     */
    custom_entity_template_root_id?: (string | null);
    /**
     * Control date for bitemporal operations
     */
    control_date?: (string | null);
    /**
     * Assigned approver
     */
    assigned_approver_id?: (string | null);
    /**
     * SLA assigned timestamp
     */
    sla_assigned_at?: (string | null);
    /**
     * SLA due date
     */
    sla_due_date?: (string | null);
    /**
     * SLA status
     */
    sla_status?: (string | null);
    /**
     * Custom field values (CHANGE_ORDER CustomEntityTemplate)
     */
    custom_fields?: (Record<string, any> | null);
    /**
     * Server-captured field-definition snapshot (read-only)
     */
    custom_field_definitions_snapshot?: (Record<string, any> | null);
};

