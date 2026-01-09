/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
/**
 * Schema for reading department data.
 */
export type DepartmentRead = {
    /**
     * Department display name
     */
    name: string;
    /**
     * UUID of the department manager
     */
    manager_id?: (string | null);
    is_active: boolean;
    /**
     * Department description
     */
    description?: (string | null);
    id: string;
    department_id: string;
    code: string;
    created_at?: (string | null);
    created_by: string;
    created_by_name?: (string | null);
    deleted_by?: (string | null);
};

