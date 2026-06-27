/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties returned to client.
 */
export type CustomEntityTemplateRead = {
    code: string;
    name: string;
    description?: (string | null);
    target_entity_type: 'PROJECT' | 'WBS_ELEMENT' | 'WORK_PACKAGE' | 'CHANGE_ORDER';
    field_definitions: Record<string, any>;
    id: string;
    custom_entity_template_id: string;
    organizational_unit_id: string;
    created_by: string;
    created_by_name?: (string | null);
    valid_time?: null;
    transaction_time?: null;
};

