/**
 * Shared account-menu item builder.
 *
 * Single source of truth for the account dropdown / sidebar account section so
 * the sidebar and `UserProfile` avatar dropdown always have RBAC parity.
 *
 * Exported as a hook (`useAccountMenuItems`) because the items embed `onClick`
 * navigations, RBAC checks (`usePermission`), the running-executions badge
 * (`useRunningExecutionsCount`), the theme switch (`useUserPreferencesStore`),
 * and the logout action (`useAuth`) — all of which are hook-driven.
 */

import type { MenuProps } from "antd";
import { Badge, Space, Switch, Typography } from "antd";
import {
  ApiOutlined,
  BulbOutlined,
  CloudServerOutlined,
  ClockCircleOutlined,
  ControlOutlined,
  DatabaseOutlined,
  HistoryOutlined,
  LogoutOutlined,
  RobotOutlined,
  SafetyOutlined,
  SettingOutlined,
  TagsOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

import { useAuth } from "@/hooks/useAuth";
import { usePermission } from "@/hooks/usePermission";
import { useUserPreferencesStore } from "@/stores/useUserPreferencesStore";
import { useRunningExecutionsCount } from "@/features/ai/chat/api/useAgentExecutions";

const { Text } = Typography;

/**
 * Build the account menu items (`MenuProps["items"]`).
 *
 * Replicates `UserProfile`'s item list and gating exactly:
 *   - user-info header (disabled, no click)
 *   - Dark Mode `Switch` (stopPropagation so it doesn't close the dropdown)
 *   - Profile (`/profile`)
 *   - Agents History (gated `ai-chat`, badge = running executions)
 *   - Admin submenu (gated `hasRole("admin")` AND ≥1 visible child), with all
 *     permission-gated children
 *   - Logout
 */
export function useAccountMenuItems(): MenuProps["items"] {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { themeMode, toggleTheme } = useUserPreferencesStore();
  const { can, hasRole } = usePermission();

  // Poll running agent executions for the Agents History badge. Only shown when
  // the user can use AI chat (mirrors UserProfile).
  const runningCountQuery = useRunningExecutionsCount();
  const runningCount = can("ai-chat") ? runningCountQuery.data ?? 0 : 0;

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const getAdminItems = (): MenuProps["items"] => {
    const adminItems: MenuProps["items"] = [];

    if (can("user-read")) {
      adminItems.push({
        key: "/admin/users",
        icon: <UserOutlined />,
        label: "Users",
        onClick: () => navigate("/admin/users"),
      });
    }

    if (hasRole("admin")) {
      adminItems.push({
        key: "/admin/role-assignments",
        icon: <TeamOutlined />,
        label: "Role Assignments",
        onClick: () => navigate("/admin/role-assignments"),
      });
    }

    if (can("organizational-unit-read")) {
      adminItems.push({
        key: "/admin/organizational-units",
        icon: <TeamOutlined />,
        label: "Organizational Units",
        onClick: () => navigate("/admin/organizational-units"),
      });
    }

    if (can("cost-element-type-read")) {
      adminItems.push({
        key: "/admin/cost-element-types",
        icon: <TagsOutlined />,
        label: "Cost Element Types",
        onClick: () => navigate("/admin/cost-element-types"),
      });
    }

    if (can("cost-event-type-read")) {
      adminItems.push({
        key: "/admin/cost-event-types",
        icon: <TagsOutlined />,
        label: "Cost Event Types",
        onClick: () => navigate("/admin/cost-event-types"),
      });
    }

    if (can("ai-config-read")) {
      adminItems.push({
        key: "/admin/ai-providers",
        icon: <RobotOutlined />,
        label: "AI Providers",
        onClick: () => navigate("/admin/ai-providers"),
      });
    }

    if (can("ai-config-read")) {
      adminItems.push({
        key: "/admin/ai-assistants",
        icon: <ApiOutlined />,
        label: "AI Assistants",
        onClick: () => navigate("/admin/ai-assistants"),
      });
    }

    if (can("ai-config-read")) {
      adminItems.push({
        key: "/admin/mcp-servers",
        icon: <CloudServerOutlined />,
        label: "MCP Servers",
        onClick: () => navigate("/admin/mcp-servers"),
      });
    }

    if (can("agent-schedule-manage")) {
      adminItems.push({
        key: "/admin/agent-schedules",
        icon: <ClockCircleOutlined />,
        label: "Agent Schedules",
        onClick: () => navigate("/admin/agent-schedules"),
      });
    }

    if (hasRole("admin")) {
      adminItems.push({
        key: "/admin/rbac",
        icon: <SafetyOutlined />,
        label: "RBAC Configuration",
        onClick: () => navigate("/admin/rbac"),
      });
    }

    if (can("change-order-workflow-config-manage")) {
      adminItems.push({
        key: "/admin/change-order-config",
        icon: <ControlOutlined />,
        label: "Change Order Config",
        onClick: () => navigate("/admin/change-order-config"),
      });
    }

    if (can("system-dump-reseed")) {
      adminItems.push({
        key: "/admin/system",
        icon: <DatabaseOutlined />,
        label: "System Admin",
        onClick: () => navigate("/admin/system"),
      });
    }

    return adminItems;
  };

  const items: MenuProps["items"] = [
    {
      key: "user-info",
      label: (
        <Space orientation="vertical" size={0} style={{ padding: "4px 0" }}>
          <Text strong>{user?.full_name || "User"}</Text>
          <Text type="secondary" style={{ fontSize: "12px" }}>
            {user?.role || "viewer"}
          </Text>
        </Space>
      ),
      disabled: true,
      style: { cursor: "default" },
    },
    {
      type: "divider",
    },
    {
      key: "theme-switch",
      label: (
        <Space style={{ width: "100%", justifyContent: "space-between" }}>
          <Space>
            <BulbOutlined />
            <span>Dark Mode</span>
          </Space>
          <Switch
            size="small"
            checked={themeMode === "dark"}
            onChange={toggleTheme}
            onClick={(_, e) => e.stopPropagation()}
          />
        </Space>
      ),
    },
    {
      type: "divider",
    },
    {
      key: "profile",
      icon: <UserOutlined />,
      label: "Profile",
      onClick: () => navigate("/profile"),
    },
    // Agents History (background runs + execution history) — gated by ai-chat
    ...(can("ai-chat")
      ? [
          {
            key: "/agents-history",
            icon: <HistoryOutlined />,
            label: (
              <Badge count={runningCount} size="small" offset={[6, 0]}>
                Agents History
              </Badge>
            ),
            onClick: () => navigate("/agents-history"),
          },
        ]
      : []),
    // Admin submenu section
    ...(hasRole("admin") && (getAdminItems()?.length ?? 0) > 0
      ? [
          {
            type: "divider" as const,
          },
          {
            key: "admin",
            icon: <SettingOutlined />,
            label: "Admin",
            children: getAdminItems(),
            popupClassName: "admin-submenu",
          },
        ]
      : []),
    {
      key: "logout",
      icon: <LogoutOutlined />,
      label: "Logout",
      onClick: handleLogout,
      danger: true,
    },
  ];

  return items;
}
