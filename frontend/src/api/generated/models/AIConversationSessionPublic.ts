/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading conversation session.
 */
export type AIConversationSessionPublic = {
    id: string;
    user_id: string;
    assistant_config_id: string;
    title: (string | null);
    /**
     * Optional project context
     */
    project_id?: (string | null);
    /**
     * Optional branch or change order context
     */
    branch_id?: (string | null);
    created_at: string;
    updated_at: string;
};

