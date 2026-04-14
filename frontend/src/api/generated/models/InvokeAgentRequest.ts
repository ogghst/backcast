/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
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
    execution_mode?: InvokeAgentRequest.execution_mode;
};
export namespace InvokeAgentRequest {
    /**
     * AI tool execution mode (default: 'standard')
     */
    export enum execution_mode {
        SAFE = 'safe',
        STANDARD = 'standard',
        EXPERT = 'expert',
    }
}

