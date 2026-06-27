/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties required for creating a Custom Entity Template.
 */
export type CustomEntityTemplateCreate = {
    code: string;
    name: string;
    description?: (string | null);
    target_entity_type: 'PROJECT' | 'WBS_ELEMENT' | 'WORK_PACKAGE' | 'CHANGE_ORDER';
    field_definitions: Record<string, any>;
    /**
     * Root Custom Entity Template ID (internal use only for seeding)
     */
    custom_entity_template_id?: (string | null);
    organizational_unit_id: string;
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
};

