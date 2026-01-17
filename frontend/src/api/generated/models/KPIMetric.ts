/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
/**
 * A single KPI value comparison between main and change branch.
 */
export type KPIMetric = {
    /**
     * Value in main branch
     */
    main_value?: (string | null);
    /**
     * Value in change branch
     */
    change_value?: (string | null);
    /**
     * Absolute difference (change - main)
     */
    delta?: string;
    /**
     * Percentage difference ((change - main) / main * 100), null if main is 0
     */
    delta_percent?: (number | null);
};

