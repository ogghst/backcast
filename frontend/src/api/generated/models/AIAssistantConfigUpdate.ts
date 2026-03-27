/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for updating an assistant config.
 */
export type AIAssistantConfigUpdate = {
    name?: (string | null);
    description?: (string | null);
    system_prompt?: (string | null);
    temperature?: (number | null);
    max_tokens?: (number | null);
    recursion_limit?: (number | null);
    allowed_tools?: (Array<string> | null);
    model_id?: (string | null);
    is_active?: (boolean | null);
};

