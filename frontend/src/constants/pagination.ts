/**
 * Pagination constants for the application.
 *
 * These values are used consistently across the application to ensure
 * uniform pagination behavior for tables and dropdown selectors.
 *
 * @see StandardTable component for table pagination
 * @see Modal components for dropdown pagination
 */

/**
 * Default page size for data tables.
 * Used in StandardTable and list views.
 */
export const TABLE_PAGE_SIZE = 10;

/**
 * Page size for dropdown selectors (Select components).
 * A higher limit is used here to reduce API calls while still
 * preventing massive payloads.
 */
export const DROPDOWN_PAGE_SIZE = 1000;

/**
 * Maximum page size allowed for user selection.
 * Prevents users from requesting extremely large pages.
 */
export const MAX_PAGE_SIZE = 100;
