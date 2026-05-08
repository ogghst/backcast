/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MarkReadResponse } from '../models/MarkReadResponse';
import type { PaginatedResponse_NotificationResponse_ } from '../models/PaginatedResponse_NotificationResponse_';
import type { UnreadCountResponse } from '../models/UnreadCountResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class NotificationsService {
    /**
     * List Notifications
     * List current user's notifications with pagination.
     *
     * Supports filtering to show only unread notifications.
     * Results are ordered by creation date, newest first.
     * @param page
     * @param pageSize
     * @param unreadOnly
     * @returns PaginatedResponse_NotificationResponse_ Successful Response
     * @throws ApiError
     */
    public static listNotifications(
        page: number = 1,
        pageSize: number = 20,
        unreadOnly: boolean = false,
    ): CancelablePromise<PaginatedResponse_NotificationResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/notifications',
            query: {
                'page': page,
                'page_size': pageSize,
                'unread_only': unreadOnly,
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
}
