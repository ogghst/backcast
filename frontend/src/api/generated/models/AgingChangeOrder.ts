/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Change order that is stuck or aging.
 */
export type AgingChangeOrder = {
    /**
     * Change Order ID (UUID)
     */
    change_order_id: string;
    /**
     * Business identifier (e.g., CO-2026-001)
     */
    code: string;
    /**
     * Change order title
     */
    title: string;
    /**
     * Current status
     */
    status: string;
    /**
     * Number of days in current status
     */
    days_in_status: number;
    /**
     * Impact level (LOW/MEDIUM/HIGH/CRITICAL)
     */
    impact_level?: (string | null);
    /**
     * SLA status (pending/approaching/overdue)
     */
    sla_status?: (string | null);
};

