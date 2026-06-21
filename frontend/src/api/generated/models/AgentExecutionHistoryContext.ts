/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Context block for an Agents History list item.
 *
 * Derived from the conversation session's ``context`` JSONB plus the
 * session's optional project / branch scope.
 */
export type AgentExecutionHistoryContext = {
    type?: (string | null);
    name?: (string | null);
    project_id?: (string | null);
    branch_id?: (string | null);
};

