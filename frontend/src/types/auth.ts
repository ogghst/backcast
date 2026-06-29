// Authentication-related TypeScript types matching backend schemas

export interface UserPublic {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  permissions: string[]; // List of permission strings (e.g., 'user-read', 'organizational-unit-delete')
  created_at?: string | null;
  department?: string | null;
}

// Type alias for permission strings
export type Permission =
  | "user-read"
  | "user-create"
  | "user-update"
  | "user-delete"
  | "organizational-unit-read"
  | "organizational-unit-create"
  | "organizational-unit-update"
  | "organizational-unit-delete"
  | "project-read"
  | "project-create"
  | "project-update"
  | "project-delete"
  | "wbs-element-read"
  | "wbs-element-create"
  | "wbs-element-update"
  | "wbs-element-delete"
  | "control-account-read"
  | "control-account-create"
  | "control-account-update"
  | "control-account-delete"
  | "work-package-read"
  | "work-package-create"
  | "work-package-update"
  | "work-package-delete"
  | "cost-element-read"
  | "cost-element-create"
  | "cost-element-update"
  | "cost-element-delete"
  | "cost-element-type-read"
  | "cost-element-type-create"
  | "cost-element-type-update"
  | "cost-element-type-delete"
  | "custom-entity-template-read"
  | "custom-entity-template-create"
  | "custom-entity-template-update"
  | "custom-entity-template-delete"
  | "cost-event-read"
  | "cost-event-create"
  | "cost-event-update"
  | "cost-event-delete"
  | "cost-event-type-read"
  | "cost-event-type-create"
  | "cost-event-type-update"
  | "cost-event-type-delete"
  | "cost-registration-read"
  | "cost-registration-create"
  | "cost-registration-update"
  | "cost-registration-delete"
  | "change-order-read"
  | "change-order-create"
  | "change-order-update"
  | "change-order-delete"
  | "change-order-recover"
  | "change-order-approve"
  | "change-order-escalate"
  | "change-order-workflow-config-manage"
  | "change-order-workflow-config-override"
  | "ai-config-read"
  | "ai-config-create"
  | "ai-config-update"
  | "ai-config-delete"
  | "ai-chat"
  | "dashboard-template-update"
  | "portfolio-read"
  | "role-assignment-read"
  | "role-assignment-create"
  | "role-assignment-update"
  | "role-assignment-delete"
  | "progress-entry-read"
  | "progress-entry-create"
  | "progress-entry-update"
  | "progress-entry-delete"
  | "project-budget-settings-read"
  | "project-budget-settings-update"
  | "project-documents-read"
  | "project-documents-write"
  | "project-documents-delete"
  | "mcp-server-read"
  | "mcp-server-create"
  | "mcp-server-update"
  | "mcp-server-delete"
  | "forecast-read"
  | "forecast-create"
  | "forecast-update"
  | "forecast-delete"
  | "schedule-baseline-read"
  | "schedule-baseline-create"
  | "schedule-baseline-update"
  | "schedule-baseline-delete"
  | "system-dump-reseed"
  | "agent-schedule-manage";

// Type alias for role strings.
//
// `admin`/`manager`/`viewer` are the platform roles; `cost-controller` and
// `pmo-director` are functional roles seeded for the Phase 2 role-curated
// PortfolioPage. Functional roles are role-curated only — they do not grant
// platform permissions beyond what `portfolio-read` allows.
export type Role =
  | "admin"
  | "manager"
  | "viewer"
  | "cost-controller"
  | "pmo-director";

// Token types - re-exported from @/api/generated
export type { Token, TokenResponse } from "@/api/generated";

export interface UserLogin {
  email: string;
  password: string;
}

export interface LoginFormData {
  username: string; // OAuth2 uses 'username' field
  password: string;
}
