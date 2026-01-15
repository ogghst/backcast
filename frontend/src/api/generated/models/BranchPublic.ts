/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for a branch option.
 */
export type BranchPublic = {
    /**
     * Branch name (e.g. 'main' or 'co-CO-123')
     */
    name: string;
    /**
     * Type of branch
     */
    type: BranchPublic.type;
    /**
     * Whether this is the default branch
     */
    is_default?: boolean;
    /**
     * Root ID of the associated change order
     */
    change_order_id?: (string | null);
    /**
     * Business code of the change order
     */
    change_order_code?: (string | null);
    /**
     * Status of the change order
     */
    change_order_status?: (string | null);
};
export namespace BranchPublic {
    /**
     * Type of branch
     */
    export enum type {
        MAIN = 'main',
        CHANGE_ORDER = 'change_order',
    }
}

