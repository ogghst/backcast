import React from "react";
import { Layout, theme, Space } from "antd";
import { Outlet, useParams } from "react-router-dom";

import { UserProfile } from "@/components/UserProfile";
import { HeaderNavigation } from "@/components/navigation/HeaderNavigation";
import {
  TimeMachineCompact,
  TimeMachineExpanded,
} from "@/components/time-machine";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import {
  useProject,
  useProjectBranches,
} from "@/features/projects/api/useProjects";
import { parseRangeLowerBound } from "@/utils/temporal";

const { Header, Content, Footer } = Layout;

const AppLayout: React.FC = () => {
  const {
    token: {
      colorBgContainer,
      colorBorder,
      colorPrimary,
      borderRadiusLG,
      fontWeightBold,
      fontSizeXL,
      paddingMD,
      paddingLG,
      paddingXL,
    },
  } = theme.useToken();

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

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{
          padding: `${paddingMD}px ${paddingLG}px`,
          background: colorBgContainer,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          height: "auto",
          minHeight: 64,
          borderBottom: `1px solid ${colorBorder}`,
        }}
      >
        {/* Left: Logo + Navigation */}
        <Space size="large" align="center">
          <div
            style={{
              fontWeight: fontWeightBold,
              fontSize: fontSizeXL,
              color: colorPrimary,
              whiteSpace: "nowrap",
            }}
          >
            Backcast
          </div>
          <HeaderNavigation />
        </Space>

        {/* Center: TimeMachine */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: paddingMD,
            flex: 1,
            justifyContent: "flex-end",
          }}
        >
          {projectId && <TimeMachineCompact projectId={projectId} />}
        </div>

        {/* Right: UserProfile */}
        <UserProfile />
      </Header>

      {/* Time Machine Expanded Panel (below header) */}
      {projectId && isTimeMachineExpanded && (
        <TimeMachineExpanded
          projectId={projectId}
          projectName={project?.name}
          timelineData={{
            startDate:
              parseRangeLowerBound(project?.valid_time ?? null) ??
              (project?.start_date ? new Date(project.start_date) : null),
            endDate: project?.end_date ? new Date(project.end_date) : null,
            branches: branches.map((b) => b.name),
            events: [], // TODO: Fetch branch events from API
          }}
        />
      )}

      <Content style={{ margin: `${paddingXL}px ${paddingMD}px 0` }}>
        <div
          style={{
            padding: paddingXL,
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
  );
};

export default AppLayout;
