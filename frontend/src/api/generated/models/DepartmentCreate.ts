/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type DepartmentCreate = {
    /**
     * Department display name
     */
    name: string;
    /**
     * UUID of the department manager
     */
    manager_id?: (string | null);
    /**
     * Whether the department is active
     */
    is_active?: boolean;
    /**
     * Unique department code (immutable)
     */
    code: string;
};

