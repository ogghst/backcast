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
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { useUserPreferencesStore } from "@/stores/useUserPreferencesStore";

const { Text } = Typography;

export const UserProfile: React.FC = () => {
  const {
    token: { colorTextSecondary },
  } = theme.useToken();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { themeMode, toggleTheme, fetchPreferences } =
    useUserPreferencesStore();

  useEffect(() => {
    if (user) {
      fetchPreferences();
    }
  }, [user, fetchPreferences]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const items: MenuProps["items"] = [
    {
      key: "user-info",
      label: (
        <Space direction="vertical" size={0} style={{ padding: "4px 0" }}>
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
