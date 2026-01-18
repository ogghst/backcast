/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EntityChangeType } from './EntityChangeType';
/**
 * A single entity change between branches.
 */
export type EntityChange = {
    /**
     * Entity ID
     */
    id: number;
    /**
     * Entity name
     */
    name: string;
    /**
     * Type of change
     */
    change_type: EntityChangeType;
    /**
     * Budget allocation change (for modified/removed)
     */
    budget_delta?: (string | null);
    /**
     * Revenue allocation change (for modified/removed)
     */
    revenue_delta?: (string | null);
    /**
     * Cost change (for modified/removed)
     */
    cost_delta?: (string | null);
};

