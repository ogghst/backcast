/**
 * Shared account-menu item builder.
 *
 * Single source of truth for the account dropdown / sidebar account section so
 * the sidebar and `UserProfile` avatar dropdown always have RBAC parity.
 *
 * Exported as a hook (`useAccountMenuItems`) because the items embed `onClick`
 * navigations, the theme switch (`useUserPreferencesStore`), and the logout
 * action (`useAuth`) — all of which are hook-driven.
 */

import type { MenuProps } from "antd";
import { Space, Switch, Typography } from "antd";
import { BulbOutlined, LogoutOutlined, UserOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

import { useAuth } from "@/hooks/useAuth";
import { useUserPreferencesStore } from "@/stores/useUserPreferencesStore";

const { Text } = Typography;

/**
 * Build the account menu items (`MenuProps["items"]`).
 *
 * Replicates `UserProfile`'s item list and gating exactly:
 *   - user-info header (disabled, no click)
 *   - Dark Mode `Switch` (stopPropagation so it doesn't close the dropdown)
 *   - Profile (`/profile`)
 *   - Logout
 *
 * Admin pages live in their own first-class sidebar section
 * (`useAdminNavItems`), not here.
 */
export function useAccountMenuItems({
  includeUserInfo = true,
}: {
  /**
   * The sidebar's account section shows the user in its own collapsible header,
   * so the menu's redundant disabled `user-info` item is omitted there. The
   * header `UserProfile` dropdown has no other name display, so it keeps it.
   */
  includeUserInfo?: boolean;
} = {}): MenuProps["items"] {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { themeMode, toggleTheme } = useUserPreferencesStore();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const items: MenuProps["items"] = [
    ...(includeUserInfo
      ? [
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
          { type: "divider" as const },
        ]
      : []),
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
