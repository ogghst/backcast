/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Structured session context for scoping AI conversations.
 *
 * Uses discriminated union pattern to validate context-specific fields.
 * Ensures type safety and prevents invalid context combinations.
 */
export type SessionContext = {
    /**
     * Context type discriminator
     */
    type: SessionContext.type;
    /**
     * Entity ID (required for non-general contexts)
     */
    id?: (string | null);
    /**
     * Project ID (for WBE and cost_element contexts)
     */
    project_id?: (string | null);
    /**
     * Optional human-readable name for the context
     */
    name?: (string | null);
};
export namespace SessionContext {
    /**
     * Context type discriminator
     */
    export enum type {
        GENERAL = 'general',
        PROJECT = 'project',
        WBE = 'wbe',
        COST_ELEMENT = 'cost_element',
    }
}

