/**
 * Sidebar Admin section item builder.
 *
 * Single source of truth for the sidebar's collapsible "Admin" section (the
 * indented, permission-gated admin-page list under the Admin toggle header in
 * `SidebarContent`). Extracted verbatim from the former account-menu admin
 * submenu (`getAdminItems` in `accountMenuItems.tsx`).
 *
 * Two-level gating:
 *   1. SECTION level — the Admin section header itself is shown only when the
 *      user `hasRole("admin")` AND at least one item is visible. This gate
 *      lives in `SidebarContent` (not here), because the header also owns the
 *      "is this section empty?" decision.
 *   2. ITEM level — each item is individually permission-gated. That filtering
 *      happens HERE, in this hook. The returned array only contains items the
 *      current user may access.
 *
 * Hook-driven (not a pure function) because every gate routes through
 * `usePermission`, which subscribes to the auth store.
 *
 * NOTE: this hook intentionally does NOT enforce the admin-role section gate.
 * It returns whatever the per-item gates permit, so a non-admin who happens to
 * hold a granular permission (e.g. `user-read`) still receives that item. The
 * section-level `hasRole("admin")` guard is the sidebar's responsibility.
 */

import {
  ApiOutlined,
  ClockCircleOutlined,
  CloudServerOutlined,
  ControlOutlined,
  DatabaseOutlined,
  RobotOutlined,
  SafetyOutlined,
  TagsOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";

import { usePermission } from "@/hooks/usePermission";

import type { NavigationItem } from "./entityNavItems";

/**
 * Build the sidebar Admin section items, filtered to those the current user may
 * access. `key` equals `path` for each item (matches the original account-menu
 * admin submenu). Order is significant — callers render in array order.
 */
export function useAdminNavItems(): NavigationItem[] {
  const { can, hasRole } = usePermission();

  // All candidates with their per-item gates. `key === path` by convention.
  const candidates: Array<{ item: NavigationItem; gate: boolean }> = [
    {
      item: {
        key: "/admin/users",
        label: "Users",
        path: "/admin/users",
        icon: <UserOutlined />,
      },
      gate: can("user-read"),
    },
    {
      item: {
        key: "/admin/role-assignments",
        label: "Role Assignments",
        path: "/admin/role-assignments",
        icon: <TeamOutlined />,
      },
      gate: hasRole("admin"),
    },
    {
      item: {
        key: "/admin/organizational-units",
        label: "Organizational Units",
        path: "/admin/organizational-units",
        icon: <TeamOutlined />,
      },
      gate: can("organizational-unit-read"),
    },
    {
      item: {
        key: "/admin/cost-element-types",
        label: "Cost Element Types",
        path: "/admin/cost-element-types",
        icon: <TagsOutlined />,
      },
      gate: can("cost-element-type-read"),
    },
    {
      item: {
        key: "/admin/cost-event-types",
        label: "Cost Event Types",
        path: "/admin/cost-event-types",
        icon: <TagsOutlined />,
      },
      gate: can("cost-event-type-read"),
    },
    {
      item: {
        key: "/admin/ai-providers",
        label: "AI Providers",
        path: "/admin/ai-providers",
        icon: <RobotOutlined />,
      },
      gate: can("ai-config-read"),
    },
    {
      item: {
        key: "/admin/ai-assistants",
        label: "AI Assistants",
        path: "/admin/ai-assistants",
        icon: <ApiOutlined />,
      },
      gate: can("ai-config-read"),
    },
    {
      item: {
        key: "/admin/mcp-servers",
        label: "MCP Servers",
        path: "/admin/mcp-servers",
        icon: <CloudServerOutlined />,
      },
      gate: can("ai-config-read"),
    },
    {
      item: {
        key: "/admin/agent-schedules",
        label: "Agent Schedules",
        path: "/admin/agent-schedules",
        icon: <ClockCircleOutlined />,
      },
      gate: can("agent-schedule-manage"),
    },
    {
      item: {
        key: "/admin/rbac",
        label: "RBAC Configuration",
        path: "/admin/rbac",
        icon: <SafetyOutlined />,
      },
      gate: hasRole("admin"),
    },
    {
      item: {
        key: "/admin/change-order-config",
        label: "Change Order Config",
        path: "/admin/change-order-config",
        icon: <ControlOutlined />,
      },
      gate: can("change-order-workflow-config-manage"),
    },
    {
      item: {
        key: "/admin/system",
        label: "System Admin",
        path: "/admin/system",
        icon: <DatabaseOutlined />,
      },
      gate: can("system-dump-reseed"),
    },
  ];

  return candidates.filter((c) => c.gate).map((c) => c.item);
}
