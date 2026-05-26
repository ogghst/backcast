/**
 * Document repository types.
 *
 * These types mirror the backend Pydantic schemas in
 * backend/app/models/schemas/document.py.
 * Once the OpenAPI client is regenerated, these can be replaced by generated types.
 */

// --- Enums ---

export type EntityType = "wbe" | "cost_element" | "change_order" | "project";

// --- Folder ---

export interface DocumentFolderCreate {
  name: string;
  parent_id?: string | null;
}

export interface DocumentFolderUpdate {
  name?: string | null;
  parent_id?: string | null;
}

export interface DocumentFolderPublic {
  id: string;
  project_id: string;
  parent_id: string | null;
  name: string;
  path: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

// --- Version ---

export interface DocumentVersionPublic {
  id: string;
  document_id: string;
  version_number: number;
  content_type: string;
  size_bytes: number;
  checksum_sha256: string;
  uploaded_by: string;
  created_at: string;
}

// --- Document ---

export interface DocumentUpdate {
  name?: string | null;
  description?: string | null;
  tags?: string[] | null;
}

export interface DocumentPublic {
  id: string;
  project_id: string;
  folder_id: string | null;
  name: string;
  extension: string;
  description: string | null;
  tags: string[];
  current_version: DocumentVersionPublic | null;
  is_locked: boolean;
  locked_by: string | null;
  created_by: string;
  size_bytes: number;
  created_at: string;
  updated_at: string;
}

// --- Entity Link ---

export interface DocumentLinkCreate {
  entity_type: EntityType;
  entity_id: string;
  note?: string | null;
}

export interface DocumentLinkUpdate {
  note: string;
}

export interface DocumentLinkPublic {
  id: string;
  document_id: string;
  entity_type: string;
  entity_id: string;
  note: string | null;
  created_at: string;
}

// --- Storage Stats ---

export interface StorageStatsPublic {
  total_bytes: number;
  file_count: number;
  version_count: number;
}

// --- Outlet context for cost element pages ---

export interface CostElementOutletContext {
  costElement: {
    cost_element_id: string;
    wbe_id: string;
    code: string;
    name: string;
    branch: string;
    [key: string]: unknown;
  } | null;
}
