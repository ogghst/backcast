import React from "react";
import { Layout, Menu, theme } from "antd";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  DashboardOutlined,
  UserOutlined,
  ProjectOutlined,
} from "@ant-design/icons";

import { UserProfile } from "@/components/UserProfile";

import { usePermission } from "@/hooks/usePermission";
import type { ItemType } from "antd/es/menu/hooks/useItems";

const { Header, Content, Footer, Sider } = Layout;

const AppLayout: React.FC = () => {
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  const navigate = useNavigate();
  const location = useLocation();
  const { can } = usePermission();

  const [collapsed, setCollapsed] = React.useState(false);

  const getMenuItems = (): ItemType[] => {
    const items: ItemType[] = [
      {
        key: "/",
        icon: <DashboardOutlined />,
        label: "Dashboard",
      },
    ];

    // Projects: No specific permission mentioned yet, assume accessible or check generic project-read if it existed
    items.push({
      key: "/projects",
      icon: <ProjectOutlined />,
      label: "Projects",
    });

    if (can("user-read")) {
      items.push({
        key: "/users",
        icon: <UserOutlined />,
        label: "Users",
      });
    }

    if (can("department-read")) {
      items.push({
        key: "/departments",
        icon: <ProjectOutlined />, // Using ProjectOutlined as placeholder if DepartmentOutlined not imported
        label: "Departments",
      });
    }

    return items;
  };

  const menuItems = getMenuItems();

  /* Logout logic moved to UserProfile component */

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={(value) => setCollapsed(value)}
        breakpoint="lg"
        collapsedWidth="0"
      >
        <div
          style={{
            height: 32,
            margin: 16,
            background: "rgba(255, 255, 255, 0.2)",
          }}
        />
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: "16px 24px",
            background: colorBgContainer,
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            height: "auto",
            minHeight: 64,
          }}
        >
          <UserProfile />
        </Header>
        <Content style={{ margin: "24px 16px 0" }}>
          <div
            style={{
              padding: 24,
              minHeight: 360,
              background: colorBgContainer,
              borderRadius: borderRadiusLG,
            }}
          >
            <Outlet />
          </div>
        </Content>
        <Footer style={{ textAlign: "center" }}>
          Backcast ©{new Date().getFullYear()}
        </Footer>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
