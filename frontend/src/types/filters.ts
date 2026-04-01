import { FilterValue } from "antd/es/table/interface";
import {
  ProjectRead,
  WBERead,
  CostElementRead,
  DepartmentRead,
  CostElementTypeRead,
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
// Whitelist: status, code, name
// Parameters: keys
export type ProjectFilters = Filterable<
  ProjectRead,
  "status" | "code" | "name"
>;

// WBEs
// Whitelist: level (mapped from 'type' in UI often, but let's check), code, name
// Note: WBERead might not have 'level' if it's computed, but let's assume it matches backend model.
// API docs say 'level' in whitelist.
export type WBEFilters = Filterable<WBERead, "code" | "name" | "level">;

// Cost Elements
// Whitelist: code, name
export type CostElementFilters = Filterable<CostElementRead, "code" | "name">;

// Users (Client-side mostly)
// Fields used in UserList.tsx: role, is_active, full_name, email, department
export type UserFilters = Filterable<
  User,
  "role" | "is_active" | "full_name" | "email" | "department"
>;

// Departments
// Fields used in DepartmentManagement.tsx: name, code, description
export type DepartmentFilters = Filterable<
  DepartmentRead,
  "name" | "code" | "description"
>;

// Cost Element Types
// Fields potentially used: department_id, name, code, description
// Note: Code/Name/Description don't have filters in UI yet, but we'll allow them for future.
export type CostElementTypeFilters = Filterable<
  CostElementTypeRead,
  "department_id" | "name" | "code" | "description"
>;
