/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for returning AI tool metadata.
 */
export type AIToolPublic = {
    name: string;
    description: string;
    permissions: Array<string>;
    category?: (string | null);
    version: string;
};

