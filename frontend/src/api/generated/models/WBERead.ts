/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading WBE data.
 */
export type WBERead = {
    id: string;
    wbe_id: string;
    project_id: string;
    code: string;
    name: string;
    /**
     * Computed budget (sum of cost element budgets in full WBE hierarchy)
     */
    budget_allocation?: string;
    /**
     * Revenue allocation from project contract value
     */
    revenue_allocation?: (string | null);
    level: number;
    parent_wbe_id?: (string | null);
    description?: (string | null);
    branch: string;
    created_at?: (string | null);
    created_by: string;
    created_by_name?: (string | null);
    parent_name?: (string | null);
    deleted_by?: (string | null);
    valid_time?: (string | null);
    transaction_time?: (string | null);
};

