import React, { useState, useEffect, useCallback } from "react";
import { Layout, theme, Space, Button, Tooltip } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { Outlet, useParams } from "react-router-dom";

import { UserProfile } from "@/components/UserProfile";
import { HeaderNavigation } from "@/components/navigation/HeaderNavigation";
import { SearchDialog, useSearchShortcut } from "@/features/search";

const BUILD_SHA = import.meta.env.VITE_GIT_SHA || "dev";
const BUILD_DATE = import.meta.env.VITE_BUILD_DATE || "dev";
import {
  TimeMachineCompact,
  TimeMachineExpanded,
} from "@/components/time-machine";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import {
  useProject,
  useProjectBranches,
} from "@/features/projects/api/useProjects";
import { parseTemporalRangeLower } from "@/utils/formatters";

const { Header, Content, Footer } = Layout;

// Mobile breakpoint for hiding logo text
const MOBILE_BREAKPOINT = 768;

const AppLayout: React.FC = () => {
  const [isMobile, setIsMobile] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const openSearch = useCallback(() => setIsSearchOpen(true), []);
  useSearchShortcut(openSearch);

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

  // Detect mobile screen size
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

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
          padding: isMobile ? `${paddingMD}px ${paddingMD}px` : `${paddingMD}px ${paddingLG}px`,
          background: colorBgContainer,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          height: "auto",
          minHeight: isMobile ? 56 : 64,
          borderBottom: `1px solid ${colorBorder}`,
          gap: isMobile ? paddingMD : paddingLG,
        }}
      >
        {/* Left: Logo + Navigation */}
        <Space size={isMobile ? "small" : "large"} align="center">
          {!isMobile && (
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
          )}
          <HeaderNavigation />
        </Space>

        {/* Center: TimeMachine (temporal menu) + Search - always visible */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: isMobile ? paddingMD : paddingLG,
            flex: 1,
            justifyContent: "flex-end",
          }}
        >
          <Tooltip title="Search (Ctrl+K)">
            <Button
              icon={<SearchOutlined />}
              onClick={openSearch}
              size="small"
            />
          </Tooltip>
          {projectId && <TimeMachineCompact projectId={projectId} />}
        </div>

        {/* Right: UserProfile - always visible */}
        <UserProfile />
      </Header>

      {/* Time Machine Expanded Panel (below header) */}
      {projectId && isTimeMachineExpanded && (
        <TimeMachineExpanded
          projectId={projectId}
          projectName={project?.name}
          timelineData={{
            startDate:
              parseTemporalRangeLower(project?.valid_time ?? null) ??
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
        <Space size="small">
          <span>Backcast ©{new Date().getFullYear()}</span>
          {BUILD_SHA && BUILD_SHA !== "dev" && BUILD_DATE && BUILD_DATE !== "dev" && (
            <span style={{ fontSize: "0.85em", opacity: 0.7 }}>
              Build: {BUILD_SHA} ({BUILD_DATE})
            </span>
          )}
        </Space>
      </Footer>

      <SearchDialog open={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
    </Layout>
  );
};

export default AppLayout;
