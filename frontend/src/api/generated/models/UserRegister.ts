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
     * Password must be at least 8 characters
     */
    password: string;
};

