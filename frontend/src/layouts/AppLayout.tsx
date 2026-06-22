import React, { Suspense, useState, useCallback, useEffect } from "react";
import { Layout, Spin, theme, Space, Button, Tooltip, Grid } from "antd";
import {
  SearchOutlined,
  MenuOutlined,
  MenuUnfoldOutlined,
  MenuFoldOutlined,
  MessageOutlined,
} from "@ant-design/icons";
import { Outlet, useParams, useNavigate, useLocation } from "react-router-dom";

import { UserProfile } from "@/components/UserProfile";
import { AppSidebar } from "@/components/navigation/AppSidebar";
import { MobileSidebarDrawer } from "@/components/navigation/MobileSidebarDrawer";
import { Can } from "@/components/auth/Can";
import { WaveBackground } from "@/components/common/WaveBackground";
import { SearchDialog, useSearchShortcut } from "@/features/search";
import { NotificationBell, useNotificationStream } from "@/features/notifications";

const BUILD_SHA = import.meta.env.VITE_GIT_SHA || "dev";
const BUILD_DATE = import.meta.env.VITE_BUILD_DATE || "dev";
import {
  TimeMachineCompact,
  TimeMachineExpanded,
} from "@/components/time-machine";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { useNavigationStore } from "@/stores/useNavigationStore";
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

const AppLayout: React.FC = () => {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const openSearch = useCallback(() => setIsSearchOpen(true), []);
  useSearchShortcut(openSearch);

  // Single notification stream connection for the whole app (badge + list).
  useNotificationStream();

  const {
    token: {
      colorBgContainer,
      colorBgLayout,
      colorBorder,
      borderRadiusLG,
      paddingMD,
      paddingLG,
      paddingXL,
    },
  } = theme.useToken();

  // Unify mobile detection on antd breakpoints so the header toggle and the
  // sidebar agree (both derive isMobile = !screens.md).
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const navigate = useNavigate();
  const location = useLocation();

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

  // Navigation UI actions for the header toggles + z-index coordination.
  const expanded = useNavigationStore((s) => s.expanded);
  const toggleExpanded = useNavigationStore((s) => s.toggleExpanded);
  const setMobileOpen = useNavigationStore((s) => s.setMobileOpen);
  const setFlyout = useNavigationStore((s) => s.setFlyout);

  // Z-index coordination (R1): when the TimeMachine panel expands, close any
  // open sidebar flyout / mobile drawer so they don't collide with it (both
  // live at the ~1000 popup tier).
  useEffect(() => {
    if (isTimeMachineExpanded) {
      setFlyout(null);
      setMobileOpen(false);
    }
  }, [isTimeMachineExpanded, setFlyout, setMobileOpen]);

  // The AI-chat launcher is redundant when already on /chat.
  const onChat = location.pathname === "/chat";

  return (
    /* `hasSider` on the OUTER Layout forces `flex-direction:row` so the rail
       (or expanded sider) and the inner header/content/footer column sit
       side-by-side. In default rail mode AppSidebar renders a plain <div>
       (not an antd <Sider>), so antd wouldn't auto-add `ant-layout-has-sider`
       and the Layout would stay in column flow — pushing header/content below
       the 100vh rail. The INNER Layout stays column (header / content / footer). */
    <Layout
      hasSider
      style={{
        minHeight: "100vh",
        background: colorBgLayout,
        position: "relative",
      }}
    >
      <WaveBackground />
      <AppSidebar />
      <Layout style={{ background: "transparent" }}>
        <Header
          style={{
            position: "relative",
            zIndex: 1,
            padding: isMobile
              ? `${paddingMD}px ${paddingMD}px`
              : `${paddingMD}px ${paddingLG}px`,
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
          {/* Left: nav affordance — hamburger on mobile, rail/expand toggle on desktop */}
          <Space size="small" align="center">
            <Tooltip
              title={isMobile ? "Menu" : expanded ? "Collapse sidebar" : "Expand sidebar"}
            >
              <Button
                type="text"
                aria-label={isMobile ? "Open menu" : expanded ? "Collapse sidebar" : "Expand sidebar"}
                icon={
                  isMobile ? (
                    <MenuOutlined />
                  ) : expanded ? (
                    <MenuFoldOutlined />
                  ) : (
                    <MenuUnfoldOutlined />
                  )
                }
                onClick={() =>
                  isMobile ? setMobileOpen(true) : toggleExpanded()
                }
              />
            </Tooltip>
          </Space>

          {/* Center: Search + TimeMachine (temporal menu) */}
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

          {/* Right: AI-Chat launcher + NotificationBell + UserProfile */}
          <Space size="small" align="center">
            <Can permission="ai-chat">
              {!onChat && (
                <Tooltip title="AI Chat">
                  <Button
                    type="text"
                    aria-label="AI Chat"
                    icon={<MessageOutlined />}
                    onClick={() =>
                      navigate("/chat", {
                        state: {
                          returnTo: location.pathname + location.search,
                        },
                      })
                    }
                  />
                </Tooltip>
              )}
            </Can>
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
            // On /chat, Content flexes to fill the available column space (the
            // header is content-driven height, so a fixed calc(100vh - 64px)
            // over/underflows). Non-chat routes keep the centered card layout.
            ...(onChat
              ? { flex: 1, minHeight: 0, margin: 0, padding: 0, maxWidth: undefined }
              : {
                  margin: "2px auto 0",
                  maxWidth: 1600,
                  width: "100%",
                  paddingLeft: isMobile ? 0 : paddingXL,
                  paddingRight: isMobile ? 0 : paddingXL,
                }),
          }}
        >
          <div
            style={
              onChat
                ? // Chat owns its own full-height layout + scroll region; render it
                  // chromeless (no card bg/border-radius). Fill the flexed Content
                  // via flex/minHeight:0 so height adapts to the real header size.
                  {
                    height: "100%",
                    flex: 1,
                    minHeight: 0,
                    margin: 0,
                    padding: 0,
                  }
                : {
                    padding: 2,
                    minHeight: 360,
                    background: colorBgContainer,
                    borderRadius: borderRadiusLG,
                    margin: 2,
                  }
            }
          >
            <Suspense fallback={<PageFallback />}>
              <Outlet />
            </Suspense>
          </div>
        </Content>
        {/* Footer suppressed on /chat so the chat view stays full-height
            (chat owns its own scroll region; the footer would push it up). */}
        {!onChat && (
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
        )}
      </Layout>

      <MobileSidebarDrawer />
      <SearchDialog open={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
    </Layout>
  );
};

export default AppLayout;
