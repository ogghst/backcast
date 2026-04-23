/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SearchResultItem } from './SearchResultItem';
/**
 * Response for the global search endpoint.
 *
 * Attributes:
 * results: Ranked list of search results.
 * total: Total number of results returned.
 * query: Original search query string.
 */
export type GlobalSearchResponse = {
    results: Array<SearchResultItem>;
    total: number;
    query: string;
};

