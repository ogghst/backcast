/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CustomerCreate } from '../models/CustomerCreate';
import type { CustomerRead } from '../models/CustomerRead';
import type { CustomerUpdate } from '../models/CustomerUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CustomersService {
    /**
     * Read Customers
     * Retrieve customers with server-side search, filtering, and sorting.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param search Search term (code, name)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCustomers(
        page: number = 1,
        perPage: number = 20,
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/customers',
            query: {
                'page': page,
                'per_page': perPage,
                'search': search,
                'filters': filters,
                'sort_field': sortField,
                'sort_order': sortOrder,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Customer
     * Create a new customer.
     * @param requestBody
     * @returns CustomerRead Successful Response
     * @throws ApiError
     */
    public static createCustomer(
        requestBody: CustomerCreate,
    ): CancelablePromise<CustomerRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/customers',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Customer
     * Get a specific customer by id.
     * @param customerId
     * @returns CustomerRead Successful Response
     * @throws ApiError
     */
    public static getCustomer(
        customerId: string,
    ): CancelablePromise<CustomerRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/customers/{customer_id}',
            path: {
                'customer_id': customerId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Customer
     * Update a customer.
     * @param customerId
     * @param requestBody
     * @returns CustomerRead Successful Response
     * @throws ApiError
     */
    public static updateCustomer(
        customerId: string,
        requestBody: CustomerUpdate,
    ): CancelablePromise<CustomerRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/customers/{customer_id}',
            path: {
                'customer_id': customerId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Customer
     * Hard delete a customer (idempotent: 204 even if absent).
     * @param customerId
     * @returns void
     * @throws ApiError
     */
    public static deleteCustomer(
        customerId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/customers/{customer_id}',
            path: {
                'customer_id': customerId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
