/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading MCP server (config shown as-is, no masking needed).
 */
export type MCPServerPublic = {
    id: string;
    name: string;
    config: Record<string, any>;
    is_active: boolean;
    created_at: string;
    updated_at: string;
};

