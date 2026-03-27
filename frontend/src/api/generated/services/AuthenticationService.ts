/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Body_login } from '../models/Body_login';
import type { RefreshRequest } from '../models/RefreshRequest';
import type { Token } from '../models/Token';
import type { TokenResponse } from '../models/TokenResponse';
import type { UserPublic } from '../models/UserPublic';
import type { UserRegister } from '../models/UserRegister';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuthenticationService {
    /**
     * Register
     * Register a new user.
     * @param requestBody
     * @returns UserPublic Successful Response
     * @throws ApiError
     */
    public static register(
        requestBody: UserRegister,
    ): CancelablePromise<UserPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/auth/register',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Login
     * OAuth2 compatible token login, get an access token and refresh token for future requests.
     * @param formData
     * @returns TokenResponse Successful Response
     * @throws ApiError
     */
    public static login(
        formData: Body_login,
    ): CancelablePromise<TokenResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/auth/login',
            formData: formData,
            mediaType: 'application/x-www-form-urlencoded',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Users Me
     * Get current user profile with RBAC permissions.
     *
     * Returns user data including their role-based permissions for use
     * in frontend authorization checks.
     * @returns UserPublic Successful Response
     * @throws ApiError
     */
    public static getCurrentUser(): CancelablePromise<UserPublic> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/auth/me',
        });
    }
    /**
     * Refresh Token
     * Refresh access token using a valid refresh token.
     *
     * Returns a new access token if the refresh token is valid, not expired,
     * and not revoked.
     * @param requestBody
     * @returns Token Successful Response
     * @throws ApiError
     */
    public static refreshToken(
        requestBody: RefreshRequest,
    ): CancelablePromise<Token> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/auth/refresh',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Logout
     * Logout user by revoking their refresh token.
     *
     * The access token will still be valid until it expires, but the
     * refresh token cannot be used to get new access tokens.
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static logout(
        requestBody: RefreshRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/auth/logout',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
