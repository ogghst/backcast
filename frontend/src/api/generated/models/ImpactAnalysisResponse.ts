/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EntityChanges } from './EntityChanges';
import type { ForecastChanges } from './ForecastChanges';
import type { KPIScorecard } from './KPIScorecard';
import type { TimeSeriesData } from './TimeSeriesData';
import type { WaterfallSegment } from './WaterfallSegment';
/**
 * Complete impact analysis response for a change order.
 */
export type ImpactAnalysisResponse = {
    /**
     * Change Order ID (UUID)
     */
    change_order_id: string;
    /**
     * Branch name being compared (e.g., 'BR-CO-2026-001')
     */
    branch_name: string;
    /**
     * Main branch name (always 'main')
     */
    main_branch_name: string;
    /**
     * KPI comparison
     */
    kpi_scorecard: KPIScorecard;
    /**
     * Entity changes
     */
    entity_changes: EntityChanges;
    /**
     * Waterfall chart data
     */
    waterfall?: Array<WaterfallSegment>;
    /**
     * S-curve comparison data
     */
    time_series?: Array<TimeSeriesData>;
    /**
     * Forecast impact analysis (EAC comparisons)
     */
    forecast_changes?: (ForecastChanges | null);
};

