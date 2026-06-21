/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DelegationConfig } from './DelegationConfig';
/**
 * Schema for updating an assistant config.
 */
export type AIAssistantConfigUpdate = {
    name?: (string | null);
    description?: (string | null);
    presentation_prompt?: (string | null);
    system_prompt?: (string | null);
    /**
     * Custom planner prompt template for main agents.
     */
    planner_prompt?: (string | null);
    /**
     * Custom supervisor prompt template. Supports {specialist_section} and {plan_section} placeholders.
     */
    supervisor_prompt?: (string | null);
    temperature?: (number | null);
    max_tokens?: (number | null);
    recursion_limit?: (number | null);
    max_supervisor_iterations?: (number | null);
    /**
     * RBAC role for tool filtering
     */
    default_role?: (string | null);
    model_id?: (string | null);
    is_active?: (boolean | null);
    agent_type?: ('main' | 'specialist' | null);
    allowed_tools?: (Array<string> | null);
    delegation_config?: (DelegationConfig | null);
    structured_output_schema?: (string | null);
};

