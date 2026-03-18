/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading assistant config.
 */
export type AIAssistantConfigPublic = {
    name: string;
    description?: (string | null);
    model_id: string;
    system_prompt?: (string | null);
    temperature?: (number | null);
    max_tokens?: (number | null);
    /**
     * List of tool names this assistant can use
     */
    allowed_tools?: (Array<string> | null);
    is_active?: boolean;
    id: string;
    created_at: string;
    updated_at: string;
};

