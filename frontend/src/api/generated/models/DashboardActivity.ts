/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for a single dashboard activity item.
 *
 * Represents a recently updated entity with metadata for display.
 */
export type DashboardActivity = {
    /**
     * Entity identifier
     */
    entity_id: string;
    /**
     * Entity name/code
     */
    entity_name: string;
    /**
     * Entity type (project, wbe, cost_element, change_order)
     */
    entity_type: string;
    /**
     * Action performed (created, updated, deleted, merged)
     */
    action: string;
    /**
     * When the action occurred
     */
    timestamp: string;
    /**
     * User who performed the action
     */
    actor_id?: (string | null);
    /**
     * Name of user who performed action
     */
    actor_name?: (string | null);
    /**
     * Parent project ID (for child entities)
     */
    project_id?: (string | null);
    /**
     * Parent project name (for child entities)
     */
    project_name?: (string | null);
    /**
     * Branch where action occurred
     */
    branch: string;
};

