/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for project metrics in spotlight.
 */
export type ProjectMetrics = {
    /**
     * Total project budget
     */
    total_budget: string;
    /**
     * Total number of WBEs
     */
    total_wbes: number;
    /**
     * Total number of cost elements
     */
    total_cost_elements: number;
    /**
     * Number of active change orders
     */
    active_change_orders: number;
    /**
     * Earned Value status (on_track, at_risk, behind)
     */
    ev_status?: (string | null);
};

