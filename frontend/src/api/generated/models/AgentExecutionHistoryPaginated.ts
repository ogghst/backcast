/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AgentExecutionHistoryItem } from './AgentExecutionHistoryItem';
/**
 * Paginated response for the Agents History page.
 */
export type AgentExecutionHistoryPaginated = {
    items: Array<AgentExecutionHistoryItem>;
    total: number;
    has_more: boolean;
};

