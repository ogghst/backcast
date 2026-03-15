/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Statistics by impact level.
 */
export type ChangeOrderImpactStats = {
    /**
     * Impact level (LOW/MEDIUM/HIGH/CRITICAL)
     */
    impact_level: string;
    /**
     * Number of change orders at this impact level
     */
    count: number;
    /**
     * Total cost exposure for COs at this impact level
     */
    total_value?: (string | null);
};

