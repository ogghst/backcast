import React, { useEffect } from "react";
import { Avatar, Dropdown, Space, Typography, theme } from "antd";
import { UserOutlined, DownOutlined } from "@ant-design/icons";
import { useAuth } from "@/hooks/useAuth";
import { useUserPreferencesStore } from "@/stores/useUserPreferencesStore";
import { useAccountMenuItems } from "@/components/navigation/accountMenuItems";

const { Text } = Typography;

export const UserProfile: React.FC = () => {
  const {
    token: { colorTextSecondary },
  } = theme.useToken();
  const { user } = useAuth();
  const { fetchPreferences } = useUserPreferencesStore();

  // Account menu items (RBAC parity with the sidebar account section).
  const items = useAccountMenuItems();

  useEffect(() => {
    if (user) {
      fetchPreferences();
    }
  }, [user, fetchPreferences]);

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
