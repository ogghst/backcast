/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MarkReadResponse } from '../models/MarkReadResponse';
import type { NotificationPreferencesResponse } from '../models/NotificationPreferencesResponse';
import type { NotificationPreferenceUpdateRequest } from '../models/NotificationPreferenceUpdateRequest';
import type { PaginatedResponse_NotificationResponse_ } from '../models/PaginatedResponse_NotificationResponse_';
import type { TelegramConnectResponse } from '../models/TelegramConnectResponse';
import type { TelegramStatusResponse } from '../models/TelegramStatusResponse';
import type { UnreadCountResponse } from '../models/UnreadCountResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class NotificationsService {
    /**
     * List Notifications
     * List current user's notifications with pagination and filters.
     *
     * Supports filtering to unread only, by category (event_type prefix), and by
     * severity. Results are ordered by creation date, newest first.
     * @param page
     * @param pageSize
     * @param unreadOnly
     * @param category Category prefix filter (e.g. 'co', 'agent')
     * @param severity Exact severity filter
     * @returns PaginatedResponse_NotificationResponse_ Successful Response
     * @throws ApiError
     */
    public static listNotifications(
        page: number = 1,
        pageSize: number = 20,
        unreadOnly: boolean = false,
        category?: (string | null),
        severity?: (string | null),
    ): CancelablePromise<PaginatedResponse_NotificationResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/notifications',
            query: {
                'page': page,
                'page_size': pageSize,
                'unread_only': unreadOnly,
                'category': category,
                'severity': severity,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Mark Notification Read
     * Mark a single notification as read.
     *
     * Returns 404 if the notification does not exist or does not belong
     * to the current user.
     * @param notificationId
     * @returns MarkReadResponse Successful Response
     * @throws ApiError
     */
    public static markNotificationRead(
        notificationId: string,
    ): CancelablePromise<MarkReadResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/notifications/{notification_id}/read',
            path: {
                'notification_id': notificationId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Mark All Notifications Read
     * Mark all unread notifications as read for the current user.
     * @returns MarkReadResponse Successful Response
     * @throws ApiError
     */
    public static markAllNotificationsRead(): CancelablePromise<MarkReadResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/notifications/read-all',
        });
    }
    /**
     * Get Unread Count
     * Get the count of unread notifications for the current user.
     *
     * Used by the frontend notification badge to display the unread count.
     * @returns UnreadCountResponse Successful Response
     * @throws ApiError
     */
    public static getUnreadNotificationCount(): CancelablePromise<UnreadCountResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/notifications/unread-count',
        });
    }
    /**
     * Get Notification Preferences
     * Return merged default + override notification preferences.
     * @returns NotificationPreferencesResponse Successful Response
     * @throws ApiError
     */
    public static getNotificationPreferences(): CancelablePromise<NotificationPreferencesResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/notifications/preferences',
        });
    }
    /**
     * Update Notification Preferences
     * Upsert the current user's notification preference cells.
     * @param requestBody
     * @returns void
     * @throws ApiError
     */
    public static updateNotificationPreferences(
        requestBody: NotificationPreferenceUpdateRequest,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/notifications/preferences',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Connect Telegram
     * Create a Telegram deep-link URL for the current user.
     *
     * Returns 400 if no Telegram bot username is configured.
     * @returns TelegramConnectResponse Successful Response
     * @throws ApiError
     */
    public static connectTelegram(): CancelablePromise<TelegramConnectResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/notifications/telegram/connect',
        });
    }
    /**
     * Get Telegram Status
     * Return the current user's Telegram linkage status.
     * @returns TelegramStatusResponse Successful Response
     * @throws ApiError
     */
    public static getTelegramStatus(): CancelablePromise<TelegramStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/notifications/telegram/status',
        });
    }
    /**
     * Unlink Telegram
     * Remove the current user's Telegram linkage.
     * @returns void
     * @throws ApiError
     */
    public static unlinkTelegram(): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/notifications/telegram',
        });
    }
}
