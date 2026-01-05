/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */

import type { Body_login } from "../models/Body_login";
import type { Token } from "../models/Token";
import type { UserPublic } from "../models/UserPublic";
import type { UserRegister } from "../models/UserRegister";
import type { CancelablePromise } from "../core/CancelablePromise";
import { OpenAPI } from "../core/OpenAPI";
import { request as __request } from "../core/request";
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
      method: "POST",
      url: "/api/v1/auth/register",
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Login
   * OAuth2 compatible token login, get an access token for future requests.
   * @param formData
   * @returns Token Successful Response
   * @throws ApiError
   */
  public static login(formData: Body_login): CancelablePromise<Token> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/auth/login",
      formData: formData,
      mediaType: "application/x-www-form-urlencoded",
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
      method: "GET",
      url: "/api/v1/auth/me",
    });
  }
}
