/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
import type { EntityChange } from './EntityChange';
/**
 * Entity changes grouped by type.
 */
export type EntityChanges = {
    /**
     * Work Breakdown Element changes
     */
    wbes?: Array<EntityChange>;
    /**
     * Cost Element changes
     */
    cost_elements?: Array<EntityChange>;
};

