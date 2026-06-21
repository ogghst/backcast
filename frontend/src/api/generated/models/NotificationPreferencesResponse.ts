/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NotificationCategoryPreferences } from './NotificationCategoryPreferences';
/**
 * Merged default + override preferences for the current user.
 */
export type NotificationPreferencesResponse = {
    /**
     * Preferences grouped by category
     */
    categories?: Array<NotificationCategoryPreferences>;
};

