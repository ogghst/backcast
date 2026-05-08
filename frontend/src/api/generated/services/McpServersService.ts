/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MCPServerCreate } from '../models/MCPServerCreate';
import type { MCPServerPublic } from '../models/MCPServerPublic';
import type { MCPServerUpdate } from '../models/MCPServerUpdate';
import type { MCPToolInfo } from '../models/MCPToolInfo';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class McpServersService {
    /**
     * List Servers
     * List all MCP server configurations.
     * @param includeInactive
     * @returns MCPServerPublic Successful Response
     * @throws ApiError
     */
    public static listMcpServers(
        includeInactive: boolean = false,
    ): CancelablePromise<Array<MCPServerPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/mcp/servers',
            query: {
                'include_inactive': includeInactive,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Server
     * Create a new MCP server configuration.
     * @param requestBody
     * @returns MCPServerPublic Successful Response
     * @throws ApiError
     */
    public static createMcpServer(
        requestBody: MCPServerCreate,
    ): CancelablePromise<MCPServerPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/mcp/servers',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Server
     * Update an MCP server configuration.
     * @param serverId
     * @param requestBody
     * @returns MCPServerPublic Successful Response
     * @throws ApiError
     */
    public static updateMcpServer(
        serverId: string,
        requestBody: MCPServerUpdate,
    ): CancelablePromise<MCPServerPublic> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/mcp/servers/{server_id}',
            path: {
                'server_id': serverId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Server
     * Delete an MCP server configuration.
     * @param serverId
     * @returns void
     * @throws ApiError
     */
    public static deleteMcpServer(
        serverId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/mcp/servers/{server_id}',
            path: {
                'server_id': serverId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Test Server Connection
     * Test connection to an MCP server and return discovered tools.
     * @param serverId
     * @returns MCPToolInfo Successful Response
     * @throws ApiError
     */
    public static testMcpServerConnection(
        serverId: string,
    ): CancelablePromise<Array<MCPToolInfo>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/mcp/servers/{server_id}/test',
            path: {
                'server_id': serverId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Server Tools
     * Get cached tools for an MCP server.
     * @param serverId
     * @returns MCPToolInfo Successful Response
     * @throws ApiError
     */
    public static getMcpServerTools(
        serverId: string,
    ): CancelablePromise<Array<MCPToolInfo>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/mcp/servers/{server_id}/tools',
            path: {
                'server_id': serverId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
