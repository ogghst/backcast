/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AIChatRequest } from '../models/AIChatRequest';
import type { AIChatResponse } from '../models/AIChatResponse';
import type { AIConversationMessagePublic } from '../models/AIConversationMessagePublic';
import type { AIConversationSessionPublic } from '../models/AIConversationSessionPublic';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AiChatService {
    /**
     * Chat
     * Send a chat message using LangGraph agent.
     * @param requestBody
     * @returns AIChatResponse Successful Response
     * @throws ApiError
     */
    public static aiChat(
        requestBody: AIChatRequest,
    ): CancelablePromise<AIChatResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/ai/chat/chat',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Sessions
     * List conversation sessions for the current user.
     * @returns AIConversationSessionPublic Successful Response
     * @throws ApiError
     */
    public static listAiSessions(): CancelablePromise<Array<AIConversationSessionPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/chat/sessions',
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
}
