import React, { useEffect } from "react";
import {
  Avatar,
  Dropdown,
  Space,
  Typography,
  theme,
  MenuProps,
  Switch,
} from "antd";
import {
  UserOutlined,
  LogoutOutlined,
  DownOutlined,
  BulbOutlined,
  SettingOutlined,
  TeamOutlined,
  TagsOutlined,
  RobotOutlined,
  ApiOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { useUserPreferencesStore } from "@/stores/useUserPreferencesStore";
import { usePermission } from "@/hooks/usePermission";

const { Text } = Typography;

export const UserProfile: React.FC = () => {
  const {
    token: { colorTextSecondary },
  } = theme.useToken();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { themeMode, toggleTheme, fetchPreferences } =
    useUserPreferencesStore();
  const { can, hasRole } = usePermission();

  useEffect(() => {
    if (user) {
      fetchPreferences();
    }
  }, [user, fetchPreferences]);

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

    if (can("department-read")) {
      adminItems.push({
        key: "/admin/departments",
        icon: <TeamOutlined />,
        label: "Departments",
        onClick: () => navigate("/admin/departments"),
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
    // Admin submenu section
    ...(hasRole("admin") && getAdminItems().length > 0
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

  return (
    <Dropdown menu={{ items }} trigger={["click"]}>
      <Space style={{ cursor: "pointer" }} align="center">
        <Avatar icon={<UserOutlined />} />
        <Space
          size={4}
          style={{ display: "none", alignItems: "center" }}
          className="md:flex"
        >
          <Text strong>{user?.full_name || "User"}</Text>
          <DownOutlined
            style={{ fontSize: "12px", color: colorTextSecondary }}
          />
        </Space>
      </Space>
    </Dropdown>
  );
};
