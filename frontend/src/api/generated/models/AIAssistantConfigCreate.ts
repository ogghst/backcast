/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating an assistant config.
 */
export type AIAssistantConfigCreate = {
    name: string;
    description?: (string | null);
    model_id: string;
    system_prompt?: (string | null);
    temperature?: (number | null);
    max_tokens?: (number | null);
    /**
     * LangGraph recursion limit (maximum steps in agent execution loop)
     */
    recursion_limit?: (number | null);
    /**
     * RBAC role for tool filtering (e.g., ai-viewer, ai-manager, ai-admin)
     */
    default_role?: (string | null);
    is_active?: boolean;
};

