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
     * Department description
     */
    description?: (string | null);
    /**
     * Root Department ID (internal use only for seeding)
     */
    department_id?: (string | null);
    /**
     * Unique department code (immutable)
     */
    code: string;
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
};

