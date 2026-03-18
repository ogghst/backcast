/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating an AI model.
 */
export type AIModelCreate = {
    model_id: string;
    display_name: string;
    is_active?: boolean;
    /**
     * Provider ID (required)
     */
    provider_id: string;
};

