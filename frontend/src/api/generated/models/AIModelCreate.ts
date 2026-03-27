/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating an AI model.
 *
 * When creating via API endpoint, provider_id comes from the URL path
 * parameter and is injected by the route handler.
 */
export type AIModelCreate = {
    model_id: string;
    display_name: string;
    is_active?: boolean;
    /**
     * Provider ID (injected from path)
     */
    provider_id?: (string | null);
};

