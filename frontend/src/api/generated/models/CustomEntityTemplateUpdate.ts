/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties that can be updated.
 *
 * `target_entity_type` is included so the service can reject it explicitly
 * with a clear 400 message (immutability enforced in the service, not via
 * schema omission). It defaults to None like the other optional fields.
 */
export type CustomEntityTemplateUpdate = {
    code?: (string | null);
    name?: (string | null);
    description?: (string | null);
    target_entity_type?: ('PROJECT' | 'WBS_ELEMENT' | 'WORK_PACKAGE' | 'CHANGE_ORDER' | null);
    field_definitions?: (Record<string, any> | null);
    /**
     * Optional control date for the update (valid_time start)
     */
    control_date?: (string | null);
};

