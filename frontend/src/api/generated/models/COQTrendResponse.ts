/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { COQTrendGranularity } from './COQTrendGranularity';
import type { COQTrendPoint } from './COQTrendPoint';
/**
 * COQ trend time-series response.
 */
export type COQTrendResponse = {
    granularity: COQTrendGranularity;
    points: Array<COQTrendPoint>;
    start_date: string;
    end_date: string;
    total_points: number;
};

