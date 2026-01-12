/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for user registration.
 */
export type UserRegister = {
    email: string;
    full_name: string;
    department?: (string | null);
    role?: string;
    /**
     * Root User ID (internal use only for seeding)
     */
    user_id?: (string | null);
    /**
     * Password must be at least 8 characters
     */
    password: string;
};

