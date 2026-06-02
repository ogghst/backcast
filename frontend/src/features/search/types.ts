export type EntityType =
  | "project"
  | "wbs_element"
  | "cost_element"
  | "schedule_baseline"
  | "change_order"
  | "cost_registration"
  | "forecast"
  | "cost_event"
  | "progress_entry"
  | "user"
  | "organizational_unit"
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
  wbs_element_id: string | null;
}

export interface GlobalSearchResponse {
  results: SearchResultItem[];
  total: number;
  query: string;
}

export interface GlobalSearchParams {
  q: string;
  project_id?: string;
  wbs_element_id?: string;
  limit?: number;
}
