/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DelegationConfig } from './DelegationConfig';
/**
 * Schema for creating an assistant config.
 *
 * The ``model_id``-required-for-main-agents invariant is enforced HERE (write
 * time), mirroring ``AIConfigService._enforce_main_agent_has_model``. It is
 * intentionally NOT on the read schema ``AIAssistantConfigPublic``: a legacy
 * misconfigured row must not 500 the list endpoint (the invariant guards
 * new writes; existing bad rows are surfaced, not fatal, on read).
 */
export type AIAssistantConfigCreate = {
    name: string;
    description?: (string | null);
    /**
     * Text shown to planner/supervisor agents to describe this specialist's capabilities. Falls back to description if not set. Specialist-only.
     */
    presentation_prompt?: (string | null);
    /**
     * Model to use. Required for main agents; specialists inherit from the main agent.
     */
    model_id?: (string | null);
    system_prompt?: (string | null);
    /**
     * Custom planner prompt template for main agents. Use {specialist_section} for dynamic specialist list.
     */
    planner_prompt?: (string | null);
    /**
     * Custom supervisor prompt template for main agents. Use {specialist_section} for dynamic specialist list, {plan_section} for dynamic plan steps.
     */
    supervisor_prompt?: (string | null);
    temperature?: (number | null);
    max_tokens?: (number | null);
    /**
     * LangGraph recursion limit (maximum steps in agent execution loop)
     */
    recursion_limit?: (number | null);
    /**
     * Maximum supervisor delegation cycles per request (main agent only). Default: 5.
     */
    max_supervisor_iterations?: (number | null);
    /**
     * RBAC role for tool filtering (e.g., ai-viewer, ai-manager, ai-admin)
     */
    default_role?: (string | null);
    is_active?: boolean;
    /**
     * Agent type: 'main' (user-facing) or 'specialist' (delegated)
     */
    agent_type?: 'main' | 'specialist';
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
};

