/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for workflow state machine transition configuration.
 */
export type WorkflowTransitionsSchema = {
    /**
     * Map of source status -> list of valid target statuses
     */
    transitions: Record<string, Array<string>>;
    /**
     * Pairs of [from_status, to_status] that trigger branch lock
     */
    lock_transitions: Array<Array<string>>;
    /**
     * Pairs of [from_status, to_status] that trigger branch unlock
     */
    unlock_transitions: Array<Array<string>>;
    /**
     * Statuses that allow CO field editing
     */
    editable_statuses: Array<string>;
};

