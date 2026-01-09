import { FilterValue } from "antd/es/table/interface";
import {
  ProjectRead,
  WBERead,
  CostElementRead,
  User,
  DepartmentRead,
  CostElementTypeRead,
} from "@/api/generated";

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
export interface ProjectFilters extends Filterable<
  ProjectRead,
  "status" | "code" | "name"
> {}

// WBEs
// Whitelist: level (mapped from 'type' in UI often, but let's check), code, name
// Note: WBERead might not have 'level' if it's computed, but let's assume it matches backend model.
// API docs say 'level' in whitelist.
export interface WBEFilters extends Filterable<WBERead, "code" | "name"> {
  // WBERead might not have 'level' or 'type' directly as a simple field, or it might.
  // We can relax strictly 'keyof T' if needed, but for now strict is better.
  // If 'level' is not in WBERead, we'll see a compile error and can adjust.
}

// Cost Elements
// Whitelist: code, name
export interface CostElementFilters extends Filterable<
  CostElementRead,
  "code" | "name"
> {}

// Users (Client-side mostly)
// Fields used in UserList.tsx: role, is_active, full_name, email, department
export interface UserFilters extends Filterable<
  User,
  "role" | "is_active" | "full_name" | "email" | "department"
> {}

// Departments
// Fields used in DepartmentManagement.tsx: name, code, description
export interface DepartmentFilters extends Filterable<
  DepartmentRead,
  "name" | "code" | "description"
> {}

// Cost Element Types
// Fields potentially used: department_id, name, code, description
// Note: Code/Name/Description don't have filters in UI yet, but we'll allow them for future.
export interface CostElementTypeFilters extends Filterable<
  CostElementTypeRead,
  "department_id" | "name" | "code" | "description"
> {}
