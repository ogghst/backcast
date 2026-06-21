/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for Notification API responses.
 */
export type NotificationResponse = {
    /**
     * Notification primary key
     */
    id: string;
    /**
     * User who should receive this notification
     */
    user_id: string;
    /**
     * Dotted event code (e.g. 'co.submitted', up to 64 chars)
     */
    event_type: string;
    /**
     * Short headline for display
     */
    title: string;
    /**
     * Full notification body text
     */
    message: string;
    /**
     * Related entity type
     */
    resource_type?: (string | null);
    /**
     * Related entity UUID
     */
    resource_id?: (string | null);
    /**
     * Severity ('info'|'notice'|'warning'|'urgent')
     */
    severity?: string;
    /**
     * Originator type ('user'|'agent'|'system')
     */
    actor_type?: (string | null);
    /**
     * Originating actor UUID
     */
    actor_id?: (string | null);
    /**
     * Optional project scope UUID
     */
    project_id?: (string | null);
    /**
     * Bell-tab category derived from event_type
     */
    category?: (string | null);
    /**
     * When the user marked it as read
     */
    read_at?: (string | null);
    /**
     * When the notification was created
     */
    created_at: string;
};

