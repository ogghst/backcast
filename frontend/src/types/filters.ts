import { FilterValue } from "antd/es/table/interface";
import {
  ProjectRead,
  WBSElementRead,
  CostElementRead,
  OrganizationalUnitRead,
  CostElementTypeRead,
  CustomEntityTemplateRead,
} from "@/api/generated";
import { User } from "@/types/user";

// Base type for filter values (aligned with Ant Design)
// FilterValue is (Key | boolean)[] | null, where Key is string | number
export type FilterableValue = FilterValue | null;

// Generic type to restrict keys to allowed fields
// T is the entity type
// K is the union of keys/fields that are allowed to be filtered
export type Filterable<T, K extends keyof T> = {
  [P in K]?: FilterableValue;
};

// --- Entity Specific Filters ---

// Projects
export type ProjectFilters = Filterable<
  ProjectRead,
  "status" | "code" | "name"
>;

// WBS Elements
export type WBSElementFilters = Filterable<WBSElementRead, "code" | "name" | "level">;

// Cost Elements (EOC)
export type CostElementFilters = Filterable<
  CostElementRead,
  "cost_element_type_id" | "work_package_id"
>;

// Users (Client-side mostly)
export type UserFilters = Filterable<
  User,
  "role" | "is_active" | "full_name" | "email"
>;

// Organizational Units
export type OrganizationalUnitFilters = Filterable<
  OrganizationalUnitRead,
  "name" | "code" | "description"
>;

// Cost Element Types
export type CostElementTypeFilters = Filterable<
  CostElementTypeRead,
  "name" | "code" | "description"
>;

// Custom Entity Templates
export type CustomEntityTemplateFilters = Filterable<
  CustomEntityTemplateRead,
  "name" | "code" | "target_entity_type" | "organizational_unit_id"
>;
