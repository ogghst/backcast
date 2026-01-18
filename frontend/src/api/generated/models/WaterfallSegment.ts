/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single segment in the waterfall chart.
 */
export type WaterfallSegment = {
    /**
     * Segment label
     */
    name: string;
    /**
     * Segment value (can be negative for decreases)
     */
    value: string;
    /**
     * True if this represents a change (not a baseline)
     */
    is_delta?: boolean;
};

