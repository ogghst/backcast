/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DelegationConfig } from './DelegationConfig';
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
     * LangGraph recursion limit (maximum steps in agent execution loop)
     */
    recursion_limit?: (number | null);
    /**
     * RBAC role for tool filtering (e.g., ai-viewer, ai-manager, ai-admin)
     */
    default_role?: (string | null);
    is_active?: boolean;
    /**
     * Agent type: 'main' (user-facing) or 'specialist' (delegated)
     */
    agent_type?: AIAssistantConfigPublic.agent_type;
    /**
     * Tool whitelist for specialist agents. None means all available tools.
     */
    allowed_tools?: (Array<string> | null);
    /**
     * Delegation configuration for main agents
     */
    delegation_config?: (DelegationConfig | null);
    /**
     * Fully qualified Pydantic model class name for structured output (specialist-only)
     */
    structured_output_schema?: (string | null);
    /**
     * System agents cannot be deleted, only disabled
     */
    is_system?: boolean;
    id: string;
    created_at: string;
    updated_at: string;
};
export namespace AIAssistantConfigPublic {
    /**
     * Agent type: 'main' (user-facing) or 'specialist' (delegated)
     */
    export enum agent_type {
        MAIN = 'main',
        SPECIALIST = 'specialist',
    }
}

