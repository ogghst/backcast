/**
 * Common API Response Types
 */

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

export interface PaginationParams {
  page?: number;
  per_page?: number;
}
