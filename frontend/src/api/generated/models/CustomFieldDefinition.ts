/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CustomFieldType } from './CustomFieldType';
/**
 * Definition of a single custom field on the workflow config.
 */
export type CustomFieldDefinition = {
    /**
     * Field name
     */
    name: string;
    /**
     * Field type
     */
    type: CustomFieldType;
    /**
     * Whether the field is required
     */
    required?: boolean;
    /**
     * Options for select type fields
     */
    options?: Array<string>;
};

