/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AgentExecutionPublic } from '../models/AgentExecutionPublic';
import type { AIConversationMessagePublic } from '../models/AIConversationMessagePublic';
import type { AIConversationSessionPaginated } from '../models/AIConversationSessionPaginated';
import type { AIConversationSessionPublic } from '../models/AIConversationSessionPublic';
import type { ApprovalRequest } from '../models/ApprovalRequest';
import type { InvokeAgentRequest } from '../models/InvokeAgentRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AiChatService {
    /**
     * List Sessions
     * List conversation sessions for the current user.
     *
     * Includes active agent execution status for each session, allowing
     * the frontend to display running indicators in the session list.
     *
     * Args:
     * context_type: Optional context type filter (general, project, wbe, cost_element)
     * context_id: Optional entity ID filter for scoped context
     * @param contextType Filter by context type (general, project, wbe, cost_element)
     * @param contextId Filter by specific entity ID (e.g., project UUID, WBE ID)
     * @returns AIConversationSessionPublic Successful Response
     * @throws ApiError
     */
    public static listAiSessions(
        contextType?: (string | null),
        contextId?: (string | null),
    ): CancelablePromise<Array<AIConversationSessionPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/chat/sessions',
            query: {
                'context_type': contextType,
                'context_id': contextId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Sessions Paginated
     * List chat sessions with pagination.
     *
     * Args:
     * skip: Number of sessions to skip (default: 0)
     * limit: Sessions per page (default: 10, max: 50)
     * context_type: Optional context type filter (general, project, wbe, cost_element)
     * context_id: Optional entity ID filter for scoped context
     * current_user: Authenticated user (injected)
     * config_service: AI config service (injected)
     *
     * Returns:
     * Paginated response with sessions, has_more flag, and total_count
     * @param skip
     * @param limit
     * @param contextType Filter by context type (general, project, wbe, cost_element)
     * @param contextId Filter by specific entity ID (e.g., project UUID, WBE ID)
     * @returns AIConversationSessionPaginated Successful Response
     * @throws ApiError
     */
    public static listAiSessionsPaginated(
        skip?: number,
        limit: number = 10,
        contextType?: (string | null),
        contextId?: (string | null),
    ): CancelablePromise<AIConversationSessionPaginated> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/chat/sessions/paginated',
            query: {
                'skip': skip,
                'limit': limit,
                'context_type': contextType,
                'context_id': contextId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Session Messages
     * Get messages for a conversation session.
     * @param sessionId
     * @returns AIConversationMessagePublic Successful Response
     * @throws ApiError
     */
    public static listAiSessionMessages(
        sessionId: string,
    ): CancelablePromise<Array<AIConversationMessagePublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/chat/sessions/{session_id}/messages',
            path: {
                'session_id': sessionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Session
     * Delete a conversation session.
     * @param sessionId
     * @returns void
     * @throws ApiError
     */
    public static deleteAiSession(
        sessionId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/ai/chat/sessions/{session_id}',
            path: {
                'session_id': sessionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Invoke Agent
     * Invoke an agent execution for a conversation session.
     *
     * Derives the assistant_config_id from the session's relationship.
     * Starts a background agent run that can be polled via the status endpoint.
     * @param sessionId
     * @param requestBody
     * @returns AgentExecutionPublic Successful Response
     * @throws ApiError
     */
    public static invokeAgent(
        sessionId: string,
        requestBody: InvokeAgentRequest,
    ): CancelablePromise<AgentExecutionPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/ai/chat/sessions/{session_id}/invoke',
            path: {
                'session_id': sessionId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Session Executions
     * List agent executions for a conversation session.
     * @param sessionId
     * @returns AgentExecutionPublic Successful Response
     * @throws ApiError
     */
    public static listSessionExecutions(
        sessionId: string,
    ): CancelablePromise<Array<AgentExecutionPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/chat/sessions/{session_id}/executions',
            path: {
                'session_id': sessionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Execution Status
     * Get the status of an agent execution.
     *
     * Verifies ownership by checking the execution's session belongs to
     * the current user.
     * @param executionId
     * @returns AgentExecutionPublic Successful Response
     * @throws ApiError
     */
    public static getExecutionStatus(
        executionId: string,
    ): CancelablePromise<AgentExecutionPublic> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/chat/executions/{execution_id}/status',
            path: {
                'execution_id': executionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Approve Execution
     * Approve or reject a tool execution via REST.
     *
     * Allows approving/rejecting a pending tool execution without an active
     * WebSocket connection. Looks up the InterruptNode for the execution's
     * session and registers the approval response.
     *
     * Args:
     * execution_id: UUID of the execution to approve.
     * body: ApprovalRequest with approval_id and approved flag.
     * current_user: Authenticated user (injected).
     * db: Database session (injected).
     *
     * Returns:
     * Dict with status and approved flag.
     *
     * Raises:
     * HTTPException: 404 if execution not found, 400 if approval registration fails.
     * @param executionId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static approveExecution(
        executionId: string,
        requestBody: ApprovalRequest,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/ai/chat/executions/{execution_id}/approve',
            path: {
                'execution_id': executionId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
