/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NotificationPreferenceEntry } from './NotificationPreferenceEntry';
/**
 * Bulk upsert of preference cells for the current user.
 */
export type NotificationPreferenceUpdateRequest = {
    /**
     * Cells to upsert (insert or update enabled flag)
     */
    changes: Array<NotificationPreferenceEntry>;
};

