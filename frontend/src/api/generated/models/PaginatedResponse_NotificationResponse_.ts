/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NotificationResponse } from './NotificationResponse';
export type PaginatedResponse_NotificationResponse_ = {
    /**
     * List of items for current page
     */
    items: Array<NotificationResponse>;
    /**
     * Total count of items matching filters
     */
    total: number;
    /**
     * Current page number (1-indexed)
     */
    page: number;
    /**
     * Number of items per page
     */
    per_page: number;
};

