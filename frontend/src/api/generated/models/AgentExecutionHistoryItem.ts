/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AgentExecutionHistoryContext } from './AgentExecutionHistoryContext';
/**
 * A single row in the Agents History page.
 *
 * Joins :class:`AIAgentExecution` with its conversation session (for
 * ownership + context) and the assistant config (for the display name).
 */
export type AgentExecutionHistoryItem = {
    id: string;
    name?: (string | null);
    status: string;
    execution_mode: string;
    run_in_background: boolean;
    started_at: string;
    completed_at?: (string | null);
    session_id: string;
    context: AgentExecutionHistoryContext;
    assistant_name?: (string | null);
    total_tokens?: number;
    tool_calls_count?: number;
    schedule_id?: (string | null);
};

