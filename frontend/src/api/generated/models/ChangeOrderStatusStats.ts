/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Statistics by change order status.
 */
export type ChangeOrderStatusStats = {
    /**
     * Status value (Draft, Submitted for Approval, etc.)
     */
    status: string;
    /**
     * Number of change orders in this status
     */
    count: number;
    /**
     * Total cost exposure for COs in this status
     */
    total_value?: (string | null);
};

