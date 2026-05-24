/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties required for creating a Package Type.
 */
export type PackageTypeCreate = {
    code: string;
    name: string;
    color?: string;
    /**
     * Whether this type contributes to COQ metrics
     */
    is_quality?: boolean;
    description?: (string | null);
    /**
     * Root Package Type ID (internal use only for seeding)
     */
    package_type_id?: (string | null);
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
};

