/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Entity type for EVM metrics.
 *
 * Defines the granularity level for EVM calculations:
 * - COST_ELEMENT: Individual cost element (leaf node)
 * - WBE: Work Breakdown Element (intermediate node)
 * - PROJECT: Project level (root node)
 */
export enum EntityType {
    COST_ELEMENT = 'cost_element',
    WBE = 'wbe',
    PROJECT = 'project',
}
