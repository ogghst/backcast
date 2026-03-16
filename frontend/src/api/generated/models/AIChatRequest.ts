/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for chat request.
 */
export type AIChatRequest = {
    message: string;
    /**
     * Existing session ID or None to create new
     */
    session_id?: (string | null);
    /**
     * Assistant config to use (required for new sessions)
     */
    assistant_config_id?: (string | null);
};

