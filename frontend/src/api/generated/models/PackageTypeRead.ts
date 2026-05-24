/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties returned to client.
 */
export type PackageTypeRead = {
    code: string;
    name: string;
    color?: string;
    /**
     * Whether this type contributes to COQ metrics
     */
    is_quality?: boolean;
    description?: (string | null);
    id: string;
    package_type_id: string;
    created_by: string;
};

