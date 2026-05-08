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
     * Event category (e.g. 'co_submitted')
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
     * When the user marked it as read
     */
    read_at?: (string | null);
    /**
     * When the notification was created
     */
    created_at: string;
};

