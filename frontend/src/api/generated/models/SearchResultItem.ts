/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single search result from any entity type.
 *
 * Attributes:
 * entity_type: Entity type label (e.g. "project", "wbs_element", "cost_element").
 * id: Version PK (database row ID).
 * root_id: Stable root ID (project_id, wbs_element_id, etc.).
 * code: Business code if the entity has one.
 * name: Display name if the entity has one.
 * description: Description text if available.
 * status: Status field if the entity has one.
 * relevance_score: Computed relevance score (0.0 - 1.0).
 * project_id: Owning project root ID for project-scoped entities.
 * wbs_element_id: Owning WBSElement root ID for WBSElement-scoped entities.
 */
export type SearchResultItem = {
    entity_type: string;
    id: string;
    root_id: string;
    code?: (string | null);
    name?: (string | null);
    description?: (string | null);
    status?: (string | null);
    relevance_score: number;
    project_id?: (string | null);
    wbs_element_id?: (string | null);
};

