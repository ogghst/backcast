export type EntityType =
  | "project"
  | "wbe"
  | "cost_element"
  | "schedule_baseline"
  | "change_order"
  | "cost_registration"
  | "forecast"
  | "quality_event"
  | "progress_entry"
  | "user"
  | "department"
  | "cost_element_type";

export interface SearchResultItem {
  entity_type: EntityType;
  id: string;
  root_id: string;
  code: string | null;
  name: string | null;
  description: string | null;
  status: string | null;
  relevance_score: number;
  project_id: string | null;
  wbe_id: string | null;
}

export interface GlobalSearchResponse {
  results: SearchResultItem[];
  total: number;
  query: string;
}

export interface GlobalSearchParams {
  q: string;
  project_id?: string;
  wbe_id?: string;
  limit?: number;
}
