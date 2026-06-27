/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectStatus } from './ProjectStatus';
/**
 * Schema for creating a new project.
 */
export type ProjectCreate = {
    /**
     * Project name
     */
    name: string;
    /**
     * Unique project code
     */
    code: string;
    /**
     * Contract value
     */
    contract_value?: (number | string | null);
    /**
     * ISO 4217 currency code
     */
    currency?: string;
    /**
     * Project status
     */
    status?: ProjectStatus;
    /**
     * Project start date
     */
    start_date?: (string | null);
    /**
     * Project end date
     */
    end_date?: (string | null);
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
     * Root Project ID (internal use only for seeding)
     */
    project_id?: (string | null);
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

