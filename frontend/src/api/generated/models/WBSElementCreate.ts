/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating a new WBS Element.
 */
export type WBSElementCreate = {
    /**
     * Parent project root ID
     */
    project_id: string;
    /**
     * WBS code (e.g., 1.2.3)
     */
    code: string;
    /**
     * WBS Element name
     */
    name: string;
    /**
     * Revenue allocation from project contract value
     */
    revenue_allocation?: (number | string | null);
    /**
     * Hierarchy level
     */
    level?: number;
    /**
     * Parent WBS Element root ID
     */
    parent_wbs_element_id?: (string | null);
    /**
     * Description
     */
    description?: (string | null);
    /**
     * Admin-template custom field values
     */
    custom_fields?: (Record<string, any> | null);
    /**
     * Bound CustomEntityTemplate root ID
     */
    custom_entity_template_root_id?: (string | null);
    /**
     * Root WBS Element ID (internal use only for seeding)
     */
    wbs_element_id?: (string | null);
    /**
     * Branch name for creation (defaults to main if not specified)
     */
    branch?: string;
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
    /**
     * Server-captured field-definition snapshot (read-only)
     */
    custom_field_definitions_snapshot?: (Record<string, any> | null);
};

