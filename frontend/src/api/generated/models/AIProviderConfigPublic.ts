/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading provider config (values masked if encrypted).
 */
export type AIProviderConfigPublic = {
    id: string;
    provider_id: string;
    key: string;
    /**
     * ***MASKED***
     */
    value?: (string | null);
    is_encrypted: boolean;
    created_at: string;
    updated_at: string;
};

