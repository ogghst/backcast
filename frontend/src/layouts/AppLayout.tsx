import React, { Suspense, useState, useEffect, useCallback } from "react";
import { Layout, Spin, theme, Space, Button, Tooltip } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { Outlet, useParams } from "react-router-dom";

import { UserProfile } from "@/components/UserProfile";
import { HeaderNavigation } from "@/components/navigation/HeaderNavigation";
import { WaveBackground } from "@/components/common/WaveBackground";
import { SearchDialog, useSearchShortcut } from "@/features/search";
import { NotificationBell } from "@/features/notifications";

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

// Fallback shown while a lazily-loaded route chunk is fetched.
const PageFallback = () => (
  <div
    style={{
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      minHeight: "60vh",
    }}
  >
    <Spin size="large" />
  </div>
);

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
      colorBgLayout,
      colorBorder,
      colorPrimary,
      borderRadiusLG,
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
  const { data: project } = useProject(projectId ?? undefined);

  // Fetch branches for the project (main + change order branches)
  const { data: branches = [] } = useProjectBranches(projectId ?? undefined);

  // Time machine expanded state
  const isTimeMachineExpanded = useTimeMachineStore((s) => s.isExpanded);

  return (
    <Layout style={{ minHeight: "100vh", background: colorBgLayout, position: "relative" }}>
      <WaveBackground />
      <Header
        style={{
          position: "relative",
          zIndex: 1,
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
                fontWeight: 600,
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
          <TimeMachineCompact projectId={projectId ?? undefined} />
        </div>

        {/* Right: NotificationBell + UserProfile - always visible */}
        <Space size="small" align="center">
          <NotificationBell />
          <UserProfile />
        </Space>
      </Header>

      {/* Time Machine Expanded Panel (below header) */}
      {isTimeMachineExpanded && (
        <TimeMachineExpanded
          projectId={projectId ?? undefined}
          projectName={project?.name}
          timelineData={projectId ? {
            startDate: (() => {
              const parsed = parseTemporalRangeLower(project?.valid_time ?? null);
              if (parsed) {
                const d = new Date(parsed);
                return isNaN(d.getTime()) ? null : d;
              }
              if (project?.start_date) {
                const d = new Date(project.start_date);
                return isNaN(d.getTime()) ? null : d;
              }
              return null;
            })(),
            endDate: (() => {
              if (!project?.end_date) return null;
              const d = new Date(project.end_date);
              return isNaN(d.getTime()) ? null : d;
            })(),
            branches: branches.map((b) => b.name),
            events: [], // TODO: Fetch branch events from API
          } : undefined}
        />
      )}

      <Content
        style={{
          position: "relative",
          zIndex: 1,
          margin: "2px auto 0",
          maxWidth: 1600,
          width: "100%",
          paddingLeft: isMobile ? 0 : paddingXL,
          paddingRight: isMobile ? 0 : paddingXL,
        }}
      >
        <div
          style={{
            padding: 2,
            minHeight: 360,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            margin: 2,
          }}
        >
          <Suspense fallback={<PageFallback />}>
            <Outlet />
          </Suspense>
        </div>
      </Content>
      <Footer style={{ position: "relative", zIndex: 1, textAlign: "center", background: "transparent" }}>
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
