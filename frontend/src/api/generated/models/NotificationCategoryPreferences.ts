/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NotificationPreferenceEntry } from './NotificationPreferenceEntry';
/**
 * Preferences grouped under a single bell-tab category.
 */
export type NotificationCategoryPreferences = {
    /**
     * Category identifier (e.g. 'change_order')
     */
    category: string;
    /**
     * Human-readable category label
     */
    label: string;
    /**
     * Per-(event_type, channel) entries
     */
    entries?: Array<NotificationPreferenceEntry>;
};

