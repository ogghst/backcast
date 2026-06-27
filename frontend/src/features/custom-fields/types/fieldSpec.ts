/**
 * Field-spec shape for a CustomEntityTemplate's `field_definitions`.
 *
 * `field_definitions` is a DICT keyed by field code; each value is one of these
 * specs. The shape mirrors the backend FIELD_REGISTRY (snake_case keys):
 *   `{ type, label, required?, default?, options?, max_length?, target_entity? }`
 *
 * The code itself appears ONLY as the dict key (the backend injects it into the
 * spec via `build_field({**spec, "code": code})`), so it is not part of FieldSpec.
 */

/** Discriminator strings, authoritative from backend FIELD_REGISTRY. */
export const FIELD_TYPES = [
  "text",
  "number",
  "decimal",
  "integer",
  "date",
  "datetime",
  "boolean",
  "select",
  "multiselect",
  "indicator",
  "reference",
  "formula",
] as const;

export type FieldType = (typeof FIELD_TYPES)[number];

/** Entity targets supported by `reference` fields (MVP: user only). */
export type ReferenceTarget = "user";

export interface FieldSpec {
  type: FieldType;
  label: string;
  /** Marks the field required; the renderer adds an antd `required` rule. */
  required?: boolean;
  /**
   * When true, this field's values are surfaced to the AI assistant. Opt-in
   * (default OFF) for confidentiality; the backend read tools filter on
   * `spec.get("ai_visible") is True`, so this must be a top-level spec key.
   */
  ai_visible?: boolean;
  /**
   * When true, this field's values are included in global search and can be
   * used as a list filter. Opt-in (default OFF); INDEPENDENT of `ai_visible`
   * (a field can be searchable but not surfaced to the AI). The backend read
   * tools filter on `spec.get("searchable") is True`, so this must be a
   * top-level spec key.
   */
  searchable?: boolean;
  /** Default value applied when the field is unset. */
  default?: unknown;
  /** Options for select / multiselect / indicator fields. */
  options?: string[];
  /** Max length for text fields. */
  max_length?: number;
  /** Target entity for reference fields. */
  target_entity?: ReferenceTarget;
  // Allow forward-compat with backend-added keys without loosening the core.
  [extra: string]: unknown;
}

/** The stored `field_definitions` dict: `{ code: spec }`. */
export type FieldDefinitions = Record<string, FieldSpec>;

/** Stored custom-field VALUES — a flat `{ code: value }` dict. */
export type CustomFieldsValue = Record<string, unknown>;

/** Entity types that can carry custom fields (matches backend enum). */
export type TargetEntityType =
  | "PROJECT"
  | "WBS_ELEMENT"
  | "WORK_PACKAGE"
  | "CHANGE_ORDER";
