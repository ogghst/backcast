/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ExecutionMode } from './ExecutionMode';
/**
 * Schema for reading agent execution records.
 */
export type AgentExecutionPublic = {
    id: string;
    session_id: string;
    status: string;
    started_at: string;
    completed_at?: (string | null);
    error_message?: (string | null);
    execution_mode?: ExecutionMode;
    total_tokens?: number;
    tool_calls_count?: number;
    created_at: string;
    updated_at: string;
};

