/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */

import type { UserHistory } from "../models/UserHistory";
import type { UserPreferenceResponse } from "../models/UserPreferenceResponse";
import type { UserPreferenceUpdate } from "../models/UserPreferenceUpdate";
import type { UserPublic } from "../models/UserPublic";
import type { UserRegister } from "../models/UserRegister";
import type { UserUpdate } from "../models/UserUpdate";
import type { CancelablePromise } from "../core/CancelablePromise";
import { OpenAPI } from "../core/OpenAPI";
import { request as __request } from "../core/request";
export class UsersService {
  /**
   * Read Users
   * Retrieve users.
   * Only Admins can list all users.
   * @param skip
   * @param limit
   * @returns UserPublic Successful Response
   * @throws ApiError
   */
  public static getUsers(
    skip?: number,
    limit: number = 100,
  ): CancelablePromise<Array<UserPublic>> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/users",
      query: {
        skip: skip,
        limit: limit,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Create User
   * Create a new user.
   * Admin only.
   * @param requestBody
   * @returns UserPublic Successful Response
   * @throws ApiError
   */
  public static createUser(
    requestBody: UserRegister,
  ): CancelablePromise<UserPublic> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/users",
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get My Preferences
   * Get current user's preferences.
   * Requires read permission.
   * @returns UserPreferenceResponse Successful Response
   * @throws ApiError
   */
  public static getMyPreferences(): CancelablePromise<UserPreferenceResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/users/me/preferences",
    });
  }
  /**
   * Update My Preferences
   * Update current user's preferences.
   * Requires update permission.
   * @param requestBody
   * @returns UserPreferenceResponse Successful Response
   * @throws ApiError
   */
  public static updateMyPreferences(
    requestBody: UserPreferenceUpdate,
  ): CancelablePromise<UserPreferenceResponse> {
    return __request(OpenAPI, {
      method: "PUT",
      url: "/api/v1/users/me/preferences",
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Read User
   * Get a specific user by id.
   * Admin can get any user. Users can only get themselves.
   * Requires read permission.
   * @param userId
   * @returns UserPublic Successful Response
   * @throws ApiError
   */
  public static getUser(userId: string): CancelablePromise<UserPublic> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/users/{user_id}",
      path: {
        user_id: userId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Update User
   * Update a user.
   * Admin can update any user. Users can only update themselves.
   * Requires update permission.
   * @param userId
   * @param requestBody
   * @returns UserPublic Successful Response
   * @throws ApiError
   */
  public static updateUser(
    userId: string,
    requestBody: UserUpdate,
  ): CancelablePromise<UserPublic> {
    return __request(OpenAPI, {
      method: "PUT",
      url: "/api/v1/users/{user_id}",
      path: {
        user_id: userId,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Delete User
   * Soft delete a user.
   * Admin only.
   * @param userId
   * @returns void
   * @throws ApiError
   */
  public static deleteUser(userId: string): CancelablePromise<void> {
    return __request(OpenAPI, {
      method: "DELETE",
      url: "/api/v1/users/{user_id}",
      path: {
        user_id: userId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get User History
   * Get version history for a user.
   * Admin can view any user's history. Users can only view their own.
   * Requires read permission.
   * @param userId
   * @returns UserHistory Successful Response
   * @throws ApiError
   */
  public static getUserHistory(
    userId: string,
  ): CancelablePromise<Array<UserHistory>> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/users/{user_id}/history",
      path: {
        user_id: userId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
}
