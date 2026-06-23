/**
 * Desktop sidebar — rail (56px) or expanded (260px).
 *
 * Mobile returns `null` (the `MobileSidebarDrawer` handles `< md`). On desktop:
 *   - `expanded === true`  → antd `Layout.Sider width={260}` rendering
 *     `<SidebarContent/>` (brand + primary/entity nav + chat + account footer).
 *     The flyout is forced off (an effect clears it) — expanded mode shows
 *     everything inline.
 *   - `expanded === false` → a 56px fixed rail of icon buttons:
 *       brand glyph (top) → Dashboard, Projects, [entity icon if on an entity
 *       route], Chat, spacer, Account (avatar) pinned at the bottom.
 *     Dashboard/Projects/Chat icons navigate immediately (rail stays) — Chat
 *     goes to `/chat`. The entity icon toggles the inline `SidebarFlyout`; the
 *     Account avatar EXPANDS the sidebar (the account menu is then the avatar
 *     dropdown in expanded mode).
 *
 * Expand/collapse is owned by the header toggle in `AppLayout`, so there is
 * exactly ONE expand affordance and nothing sits under the account avatar.
 * Pinned to the viewport via `position:sticky; height:100dvh` — `dvh` accounts
 * for mobile/tablet browser chrome, so the account never falls below the fold.
 *
 * Craft: ≥44px touch targets on every rail icon, antd `Tooltip` labels, active
 * highlight via theme tokens, smooth width transition.
 */

import { useEffect } from "react";
import { Badge, Button, Grid, Layout, Tooltip, theme } from "antd";
import {
  AppstoreOutlined,
  HomeOutlined,
  MessageOutlined,
  ProjectOutlined,
  RobotOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";

import { useAdminNavItems } from "@/components/navigation/adminNavItems";
import { SidebarContent } from "@/components/navigation/SidebarContent";
import { SidebarFlyout } from "@/components/navigation/SidebarFlyout";
import { useEntityNav } from "@/components/navigation/useEntityNav";
import { serializeCtx } from "@/hooks/navigation/useChatContextFromUrl";
import { useEffectiveChatContext } from "@/hooks/navigation/useEffectiveChatContext";
import { useRunningExecutionsCount } from "@/features/ai/chat/api/useAgentExecutions";
import type { NavFlyout } from "@/stores/useNavigationStore";
import { useNavigationStore } from "@/stores/useNavigationStore";
import { usePermission } from "@/hooks/usePermission";

const { Sider } = Layout;

const RAIL_WIDTH = 56;
const EXPANDED_WIDTH = 260;

/**
 * A 44px rail icon button. Active highlight via theme tokens; tooltip label
 * shown on hover/focus. The `active` prop paints the icon in primary and gives
 * the row a primary-tinted background.
 *
 * `stopsMouseDown` (opt-in): for buttons that TOGGLE the flyout (the entity
 * icon), stopping mousedown propagation prevents the SidebarFlyout
 * outside-click listener from firing on the button's own mousedown and closing
 * the flyout before the subsequent click reopens it (the double-toggle bug).
 */
function RailButton({
  label,
  icon,
  active,
  onClick,
  stopsMouseDown = false,
  badge,
}: {
  label: string;
  icon: React.ReactNode;
  active?: boolean;
  onClick: () => void;
  stopsMouseDown?: boolean;
  /** Optional count to badge the icon corner (auto-hidden at 0 by antd). */
  badge?: number;
}) {
  const { token } = theme.useToken();
  const inner = (
    <span style={{ fontSize: token.fontSizeLG, display: "inline-flex" }}>
      {icon}
    </span>
  );
  const iconEl =
    badge !== undefined ? (
      <Badge count={badge} offset={[-2, 2]}>
        {inner}
      </Badge>
    ) : (
      inner
    );
  return (
    <Tooltip title={label} placement="right">
      <Button
        type="text"
        aria-label={label}
        onClick={onClick}
        onMouseDown={stopsMouseDown ? (e) => e.stopPropagation() : undefined}
        style={{
          width: RAIL_WIDTH,
          height: 44, // ≥44px touch target
          borderRadius: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: active ? token.colorPrimary : token.colorTextSecondary,
          background: active ? token.colorPrimaryBg : "transparent",
          borderRight: active
            ? `3px solid ${token.colorPrimary}`
            : "3px solid transparent",
        }}
        icon={iconEl}
      />
    </Tooltip>
  );
}

function isPrimaryActive(pathname: string, path: string): boolean {
  if (path === "/") return pathname === "/";
  return pathname === path || pathname.startsWith(`${path}/`);
}

export function AppSidebar(): React.JSX.Element | null {
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const navigate = useNavigate();
  const location = useLocation();

  const effectiveCtx = useEffectiveChatContext();

  const { can, canAny, hasRole } = usePermission();
  const canChat = can("ai-chat");
  const canAgents = canAny(["ai-chat", "agent-schedule-manage"]);
  const agentsDest = can("agent-schedule-manage")
    ? "/admin/agent-schedules"
    : "/agents-history";
  const agentsActive =
    isPrimaryActive(location.pathname, "/admin/agent-schedules") ||
    isPrimaryActive(location.pathname, "/agents-history");
  // Poll unconditionally (Rules of Hooks); gate the value so unauthorized users
  // never show a badge. TanStack stops polling when the component unmounts.
  const runningCountQuery = useRunningExecutionsCount();
  const runningCount = canAgents ? (runningCountQuery.data ?? 0) : 0;

  const adminItems = useAdminNavItems();
  const showAdmin = hasRole("admin") && adminItems.length > 0;

  const expanded = useNavigationStore((s) => s.expanded);
  const flyout = useNavigationStore((s) => s.flyout);
  const toggleExpanded = useNavigationStore((s) => s.toggleExpanded);
  const setFlyout = useNavigationStore((s) => s.setFlyout);

  const entityNav = useEntityNav();

  // Expanded mode owns the whole content inline — never show the flyout.
  useEffect(() => {
    if (expanded && flyout !== null) setFlyout(null);
  }, [expanded, flyout, setFlyout]);

  if (isMobile) return null;

  // Toggle a flyout: open when closed or switching sections; close when the
  // same section is already open.
  const toggleFlyout = (key: Exclude<NavFlyout, null>) => {
    setFlyout(flyout === key ? null : key);
  };

  // Open the chat page directly. No-op when already on /chat so an active
  // conversation isn't reset. The current effective context is serialized into
  // the `?ctx=` URL contract so project/scope is preserved across the nav.
  // returnTo lets the in-chat Back button return here.
  const handleChatNav = () => {
    if (location.pathname === "/chat") return;
    navigate(`/chat?${serializeCtx(effectiveCtx)}`, {
      state: { returnTo: location.pathname + location.search },
    });
  };

  if (expanded) {
    return (
      <Sider
        width={EXPANDED_WIDTH}
        collapsedWidth={0}
        // Smooth transition when toggling between rail and expanded.
        // Pin to the viewport (sticky + 100dvh + alignSelf:flex-start so it
        // doesn't stretch to page height) so the account footer at the bottom is
        // always within reach on long pages — the inner nav scrolls on its own.
        // `dvh` (not `vh`) so mobile/tablet browser chrome doesn't push the
        // account below the fold.
        style={{
          position: "sticky",
          top: 0,
          height: "100dvh",
          alignSelf: "flex-start",
          background: token.colorBgContainer,
          borderRight: `1px solid ${token.colorBorderSecondary}`,
          overflow: "hidden",
          transition: "all 200ms ease",
        }}
      >
        <div style={{ height: "100%" }}>
          <SidebarContent onNavigate={() => {}} />
        </div>
      </Sider>
    );
  }

  // Rail mode.
  return (
    <>
      <div
        style={{
          position: "sticky",
          top: 0,
          alignSelf: "flex-start",
          width: RAIL_WIDTH,
          flexShrink: 0,
          height: "100dvh",
          background: token.colorBgContainer,
          borderRight: `1px solid ${token.colorBorderSecondary}`,
          display: "flex",
          flexDirection: "column",
          alignItems: "stretch",
          transition: "all 200ms ease",
        }}
      >
        {/* Brand glyph */}
        <Tooltip title="Backcast" placement="right">
          <Button
            type="text"
            aria-label="Backcast home"
            onClick={() => navigate("/")}
            style={{
              height: 56,
              width: RAIL_WIDTH,
              borderRadius: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            icon={
              <ThunderboltOutlined
                style={{
                  color: token.colorPrimary,
                  fontSize: token.fontSizeXL,
                }}
              />
            }
          />
        </Tooltip>

        {/* Primary nav */}
        <RailButton
          label="Dashboard"
          icon={<HomeOutlined />}
          active={isPrimaryActive(location.pathname, "/")}
          onClick={() => navigate("/")}
        />
        <RailButton
          label="Projects"
          icon={<AppstoreOutlined />}
          active={isPrimaryActive(location.pathname, "/projects")}
          onClick={() => navigate("/projects")}
        />

        {/* Entity tab (only on entity-detail routes) */}
        {entityNav && (
          <RailButton
            label={entityNav.label}
            icon={<ProjectOutlined />}
            active={flyout === "entity"}
            stopsMouseDown
            onClick={() => toggleFlyout("entity")}
          />
        )}

        {/* Chat — navigates to the chat page (does not open a history flyout).
            Chat history is shown inline only in expanded mode, so the rail has
            no separate history button. */}
        {canChat && (
          <RailButton
            label="Chat"
            icon={<MessageOutlined />}
            active={isPrimaryActive(location.pathname, "/chat")}
            onClick={handleChatNav}
          />
        )}

        {/* Agents — a single button below Chat. Managers (agent-schedule-manage)
            land on Schedules; chat-only users land on History. Badged with the
            running-executions count. Active on either destination route. */}
        {canAgents && (
          <RailButton
            label="Agents"
            icon={<RobotOutlined />}
            active={agentsActive}
            onClick={() => navigate(agentsDest)}
            badge={runningCount > 0 ? runningCount : undefined}
          />
        )}

        {/* Admin — opens a flyout of the permission-gated admin pages (mirrors the
            entity rail→flyout). Admin-only; expanded mode shows the inline section. */}
        {showAdmin && (
          <RailButton
            label="Admin"
            icon={<SettingOutlined />}
            active={flyout === "admin"}
            stopsMouseDown
            onClick={() => toggleFlyout("admin")}
          />
        )}

        {/* Spacer */}
        <div style={{ flex: "1 1 auto" }} />

        {/* Account avatar — pinned at the bottom of the rail. In collapsed/rail
            mode clicking it EXPANDS the sidebar (revealing the account menu via
            the avatar dropdown in expanded mode), rather than opening a flyout.
            Expand/collapse otherwise lives in the header, so nothing sits under
            the avatar. */}
        <RailButton
          label="Account"
          icon={<UserOutlined />}
          onClick={toggleExpanded}
        />
      </div>

      {/* Flyout panel — reads `flyout` from the store itself. */}
      <SidebarFlyout />
    </>
  );
}
