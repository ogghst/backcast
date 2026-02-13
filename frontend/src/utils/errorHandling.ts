/**
 * Centralized Error Handling Utilities
 *
 * Provides consistent error handling patterns across the application.
 */

import { toast } from "sonner";
import type { AxiosError } from "axios";

/**
 * Standard API error structure
 */
export interface ApiError {
  message: string;
  code?: string;
  details?: unknown;
  field?: string;
}

/**
 * Extract error message from various error types
 */
export function getErrorMessage(error: unknown): string {
  if (typeof error === "string") {
    return error;
  }

  if (error instanceof Error) {
    return error.message;
  }

  if (isAxiosError(error)) {
    const data = error.response?.data as ApiError | undefined;
    return data?.message || error.message || "An unexpected error occurred";
  }

  return "An unexpected error occurred";
}

/**
 * Type guard for AxiosError
 */
export function isAxiosError(error: unknown): error is AxiosError<ApiError> {
  return (
    typeof error === "object" &&
    error !== null &&
    "isAxiosError" in error &&
    (error as AxiosError).isAxiosError === true
  );
}

/**
 * Handle API errors with consistent user feedback
 */
export function handleApiError(error: unknown, context?: string): string {
  const message = getErrorMessage(error);
  const contextPrefix = context ? `${context}: ` : "";

  toast.error(`${contextPrefix}${message}`);

  // Log full error for debugging
  console.error("API Error:", error);

  return message;
}

/**
 * Parse validation errors from API response
 */
export function getValidationErrors(
  error: unknown
): Record<string, string[]> {
  if (isAxiosError(error)) {
    const data = error.response?.data as
      | { detail?: Array<{ msg: string; loc: string[]; type: string }> }
      | undefined;

    if (data?.detail && Array.isArray(data.detail)) {
      return data.detail.reduce((acc, err) => {
        const field = err.loc[err.loc.length - 1] || "general";
        if (!acc[field]) {
          acc[field] = [];
        }
        acc[field].push(err.msg);
        return acc;
      }, {} as Record<string, string[]>);
    }
  }

  return {};
}

/**
 * Show validation errors as toast notifications
 */
export function showValidationErrors(error: unknown): void {
  const errors = getValidationErrors(error);

  Object.entries(errors).forEach(([field, messages]) => {
    messages.forEach((message) => {
      toast.error(`${field}: ${message}`);
    });
  });
}

/**
 * Wrap async function with error handling
 */
export function withErrorHandling<T extends (...args: unknown[]) => Promise<unknown>>(
  fn: T,
  options?: {
    errorMessage?: string;
    showToast?: boolean;
    onError?: (error: unknown) => void;
  }
): T {
  return (async (...args: Parameters<T>) => {
    try {
      return await fn(...args);
    } catch (error) {
      if (options?.showToast !== false) {
        handleApiError(error, options?.errorMessage);
      }
      options?.onError?.(error);
      throw error;
    }
  }) as T;
}

/**
 * React hook mutation wrapper with error handling
 */
export function createMutationWithErrorHandling<
  TData = unknown,
  TError = unknown,
  TVariables = void,
  TContext = unknown
>(options: {
  mutationFn: (variables: TVariables) => Promise<TData>;
  onSuccess?: (data: TData, variables: TVariables, context: TContext) => void | Promise<unknown>;
  onError?: (error: TError, variables: TVariables, context: TContext) => void;
  successMessage?: string | ((data: TData) => string);
  errorMessage?: string | ((error: TError) => string);
}) {
  return {
    mutationFn: options.mutationFn,
    onSuccess: (data: TData, variables: TVariables, context: TContext) => {
      if (options.successMessage) {
        const message =
          typeof options.successMessage === "function"
            ? options.successMessage(data)
            : options.successMessage;
        toast.success(message);
      }
      return options.onSuccess?.(data, variables, context);
    },
    onError: (error: TError, variables: TVariables, context: TContext) => {
      if (options.errorMessage) {
        const message =
          typeof options.errorMessage === "function"
            ? options.errorMessage(error)
            : options.errorMessage;
        toast.error(message);
      } else {
        handleApiError(error);
      }
      return options.onError?.(error, variables, context);
    },
  };
}
