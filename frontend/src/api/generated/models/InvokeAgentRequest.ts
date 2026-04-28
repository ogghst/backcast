/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ExecutionMode } from './ExecutionMode';
/**
 * Request body for invoking an agent via REST API.
 */
export type InvokeAgentRequest = {
    /**
     * User message content
     */
    message: string;
    /**
     * AI tool execution mode (default: 'standard')
     */
    execution_mode?: ExecutionMode;
};

