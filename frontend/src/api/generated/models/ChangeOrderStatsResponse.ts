/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AgingChangeOrder } from './AgingChangeOrder';
import type { ApprovalWorkloadItem } from './ApprovalWorkloadItem';
import type { ChangeOrderImpactStats } from './ChangeOrderImpactStats';
import type { ChangeOrderStatusStats } from './ChangeOrderStatusStats';
import type { ChangeOrderTrendPoint } from './ChangeOrderTrendPoint';
/**
 * Aggregated statistics for change orders.
 *
 * Response schema for GET /api/v1/change-orders/stats endpoint.
 * Provides comprehensive analytics for the Change Order Dashboard.
 */
export type ChangeOrderStatsResponse = {
    /**
     * Total number of change orders
     */
    total_count?: number;
    /**
     * Total potential cost impact (sum of budget deltas)
     */
    total_cost_exposure?: string;
    /**
     * Total value of pending change orders (not yet approved/rejected)
     */
    pending_value?: string;
    /**
     * Total value of approved change orders
     */
    approved_value?: string;
    /**
     * Breakdown by status
     */
    by_status?: Array<ChangeOrderStatusStats>;
    /**
     * Breakdown by impact level
     */
    by_impact_level?: Array<ChangeOrderImpactStats>;
    /**
     * Cumulative cost trend over time
     */
    cost_trend?: Array<ChangeOrderTrendPoint>;
    /**
     * Average days from submission to approval (historical)
     */
    avg_approval_time_days?: (number | null);
    /**
     * Pending approvals grouped by approver
     */
    approval_workload?: Array<ApprovalWorkloadItem>;
    /**
     * Change orders that have been in the same status too long
     */
    aging_items?: Array<AgingChangeOrder>;
    /**
     * Configured threshold for aging detection
     */
    aging_threshold_days?: number;
};

