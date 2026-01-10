import React from "react";
import { Layout, Menu, theme } from "antd";
import { Outlet, useNavigate, useLocation, useParams } from "react-router-dom";
import {
  DashboardOutlined,
  UserOutlined,
  ProjectOutlined,
  SettingOutlined,
  TeamOutlined,
  TagsOutlined,
} from "@ant-design/icons";

import { UserProfile } from "@/components/UserProfile";
import {
  TimeMachineCompact,
  TimeMachineExpanded,
} from "@/components/time-machine";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { useProject } from "@/features/projects/api/useProjects";

import { usePermission } from "@/hooks/usePermission";
import type { ItemType } from "antd/es/menu/hooks/useItems";

const { Header, Content, Footer, Sider } = Layout;

const AppLayout: React.FC = () => {
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  const navigate = useNavigate();
  const location = useLocation();
  const { can, hasRole } = usePermission();

  // Extract projectId from URL if on project pages
  const params = useParams<{ projectId?: string }>();
  const projectId = params.projectId;

  // Fetch project data for timeline
  const { data: project } = useProject(projectId);

  // Time machine expanded state
  const isTimeMachineExpanded = useTimeMachineStore((s) => s.isExpanded);

  const [collapsed, setCollapsed] = React.useState(false);

  const getMenuItems = (): ItemType[] => {
    const items: ItemType[] = [
      {
        key: "/",
        icon: <DashboardOutlined />,
        label: "Dashboard",
      },
    ];

    // Projects
    items.push({
      key: "/projects",
      icon: <ProjectOutlined />,
      label: "Projects",
    });

    // Admin submenu - only visible to admins
    if (hasRole("admin")) {
      const adminItems: ItemType[] = [];

      if (can("user-read")) {
        adminItems.push({
          key: "/admin/users",
          icon: <UserOutlined />,
          label: "User Management",
        });
      }

      if (can("department-read")) {
        adminItems.push({
          key: "/admin/departments",
          icon: <TeamOutlined />,
          label: "Department Management",
        });
      }

      if (can("cost-element-type-read")) {
        adminItems.push({
          key: "/admin/cost-element-types",
          icon: <TagsOutlined />,
          label: "Cost Element Types",
        });
      }

      if (adminItems.length > 0) {
        items.push({
          key: "/admin",
          icon: <SettingOutlined />,
          label: "Admin",
          children: adminItems,
        });
      }
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
            justifyContent: "space-between",
            alignItems: "center",
            height: "auto",
            minHeight: 64,
          }}
        >
          {/* Left side: Time Machine (only when project is selected) */}
          <div style={{ display: "flex", alignItems: "center" }}>
            {projectId && <TimeMachineCompact projectId={projectId} />}
          </div>

          {/* Right side: User Profile */}
          <UserProfile />
        </Header>

        {/* Time Machine Expanded Panel (below header) */}
        {projectId && isTimeMachineExpanded && (
          <TimeMachineExpanded
            projectId={projectId}
            projectName={project?.name}
            timelineData={{
              startDate: project?.start_date
                ? new Date(project.start_date)
                : null,
              endDate: project?.end_date ? new Date(project.end_date) : null,
              branches: ["main"], // TODO: Fetch actual branches from API
              events: [], // TODO: Fetch branch events from API
            }}
          />
        )}

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
