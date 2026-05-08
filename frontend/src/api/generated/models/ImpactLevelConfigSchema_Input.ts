/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for a single impact level configuration.
 */
export type ImpactLevelConfigSchema_Input = {
    /**
     * Impact level name (LOW/MEDIUM/HIGH/CRITICAL)
     */
    level_name: string;
    /**
     * Sort order (1-4)
     */
    level_order: number;
    /**
     * Maximum amount for this level (upper bound in EUR)
     */
    threshold_amount: (number | string);
    /**
     * Minimum impact score for this level
     */
    score_threshold_min: (number | string);
    /**
     * Maximum impact score for this level
     */
    score_threshold_max: (number | string);
    /**
     * Whether this level is active
     */
    is_active?: boolean;
};

