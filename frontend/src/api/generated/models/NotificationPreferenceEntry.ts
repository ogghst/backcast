/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single per-user (event_type, channel, enabled) preference cell.
 */
export type NotificationPreferenceEntry = {
    /**
     * Registered event code or '*' wildcard
     */
    event_type: string;
    /**
     * Delivery channel (e.g. 'in_app', 'telegram')
     */
    channel: string;
    /**
     * Whether delivery on this channel is enabled
     */
    enabled: boolean;
};

