import React from "react";
import { Layout, Menu, theme, MenuProps, Alert } from "antd";
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
import { useProject, useProjectBranches } from "@/features/projects/api/useProjects";
import { parseRangeLowerBound } from "@/utils/temporal";

import { usePermission } from "@/hooks/usePermission";

const { Header, Content, Footer, Sider } = Layout;

/**
 * Check if a branch name is a change order branch (co-{code} pattern)
 */
function isChangeOrderBranch(branch: string): boolean {
  return branch.startsWith("co-");
}

const AppLayout: React.FC = () => {
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  const navigate = useNavigate();
  const location = useLocation();
  const { can, hasRole } = usePermission();

  // Extract projectId from URL if on project pages, or use store context
  const params = useParams<{ projectId?: string }>();
  const urlProjectId = params.projectId;
  const storeProjectId = useTimeMachineStore((s) => s.currentProjectId);
  const projectId = urlProjectId || storeProjectId;

  // Fetch project data for timeline
  const { data: project } = useProject(projectId);

  // Fetch branches for the project (main + change order branches)
  const { data: branches = [] } = useProjectBranches(projectId);

  // Time machine expanded state
  const isTimeMachineExpanded = useTimeMachineStore((s) => s.isExpanded);

  // Get selected branch to detect change order branches
  const selectedBranch = useTimeMachineStore((s) => s.getSelectedBranch?.() ?? "main");
  const isChangeOrderMode = isChangeOrderBranch(selectedBranch);

  const [collapsed, setCollapsed] = React.useState(false);

  const getMenuItems = (): MenuProps["items"] => {
    const items: MenuProps["items"] = [
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
      const adminItems: MenuProps["items"] = [];

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
            // Amber indicator border when in change order branch
            borderBottom: isChangeOrderMode ? "4px solid #F59E0B" : undefined,
          }}
        >
          {/* Left side: Time Machine (only when project is selected) */}
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            {projectId && <TimeMachineCompact projectId={projectId} />}
            {/* Change order mode indicator */}
            {isChangeOrderMode && (
              <Alert
                message={
                  <span style={{ fontWeight: 500 }}>
                    Change Order Mode: <strong>{selectedBranch}</strong>
                  </span>
                }
                type="warning"
                showIcon
                style={{
                  padding: "4px 12px",
                  fontSize: 13,
                  backgroundColor: "#FFF7E6",
                  borderColor: "#F59E0B",
                }}
              />
            )}
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
              startDate: parseRangeLowerBound(project?.valid_time ?? null)
                ?? (project?.start_date ? new Date(project.start_date) : null),
              endDate: project?.end_date ? new Date(project.end_date) : null,
              branches: branches.map(b => b.name),
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
