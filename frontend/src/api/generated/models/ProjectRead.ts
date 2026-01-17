/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
/**
 * Schema for reading project data.
 */
export type ProjectRead = {
    /**
     * Project name
     */
    name: string;
    /**
     * Unique project code
     */
    code: string;
    /**
     * Project budget
     */
    budget: string;
    /**
     * Contract value
     */
    contract_value?: (string | null);
    /**
     * Project status
     */
    status?: string;
    /**
     * Project start date
     */
    start_date?: (string | null);
    /**
     * Project end date
     */
    end_date?: (string | null);
    /**
     * Description
     */
    description?: (string | null);
    id: string;
    project_id: string;
    branch: string;
    created_at?: (string | null);
    created_by?: (string | null);
    created_by_name?: (string | null);
    deleted_by?: (string | null);
    valid_time?: (string | null);
    transaction_time?: (string | null);
};

