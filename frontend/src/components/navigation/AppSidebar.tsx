/**
 * Desktop sidebar — rail (56px) or expanded (260px).
 *
 * Mobile returns `null` (the `MobileSidebarDrawer` handles `< md`). On desktop:
 *   - `expanded === true`  → antd `Layout.Sider width={260}` rendering
 *     `<SidebarContent/>` plus a bottom collapse chevron. The flyout is forced
 *     off (an effect clears it) — expanded mode shows everything inline.
 *   - `expanded === false` → a 56px fixed rail of icon buttons:
 *       brand glyph (top) → Dashboard, Projects, [entity icon if on an entity
 *       route], Chat, spacer, Account (avatar), expand chevron (bottom).
 *     Dashboard/Projects/entity-tab icons navigate immediately (rail stays).
 *     Chat/Account/entity icons toggle the inline `SidebarFlyout`.
 *
 * Craft: ≥44px touch targets on every rail icon, antd `Tooltip` labels, active
 * highlight via theme tokens, smooth width transition.
 */

import { useEffect } from "react";
import { Button, Grid, Layout, Tooltip, theme } from "antd";
import {
  AppstoreOutlined,
  HomeOutlined,
  MenuFoldOutlined,
  MessageOutlined,
  ProjectOutlined,
  RightOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";

import { SidebarContent } from "@/components/navigation/SidebarContent";
import { SidebarFlyout } from "@/components/navigation/SidebarFlyout";
import { useEntityNav } from "@/components/navigation/useEntityNav";
import type { NavFlyout } from "@/stores/useNavigationStore";
import { useNavigationStore } from "@/stores/useNavigationStore";
import { usePermission } from "@/hooks/usePermission";
import { useThemeTokens } from "@/hooks/useThemeTokens";

const { Sider } = Layout;

const RAIL_WIDTH = 56;
const EXPANDED_WIDTH = 260;

/**
 * A 44px rail icon button. Active highlight via theme tokens; tooltip label
 * shown on hover/focus. The `active` prop paints the icon in primary and gives
 * the row a primary-tinted background.
 *
 * `stopsMouseDown` (opt-in): for buttons that TOGGLE the flyout (Chat/Account/
 * entity), stopping mousedown propagation prevents the SidebarFlyout
 * outside-click listener from firing on the button's own mousedown and closing
 * the flyout before the subsequent click reopens it (the double-toggle bug).
 */
function RailButton({
  label,
  icon,
  active,
  onClick,
  stopsMouseDown = false,
}: {
  label: string;
  icon: React.ReactNode;
  active?: boolean;
  onClick: () => void;
  stopsMouseDown?: boolean;
}) {
  const { token } = theme.useToken();
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
        icon={
          <span style={{ fontSize: token.fontSizeLG, display: "inline-flex" }}>
            {icon}
          </span>
        }
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
  const { spacing } = useThemeTokens();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const navigate = useNavigate();
  const location = useLocation();

  const { can } = usePermission();
  const canChat = can("ai-chat");

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

  if (expanded) {
    return (
      <Sider
        width={EXPANDED_WIDTH}
        collapsedWidth={0}
        // Smooth transition when toggling between rail and expanded.
        // Pin to the viewport (sticky + 100vh + alignSelf:flex-start so it
        // doesn't stretch to page height) so the account menu at the bottom is
        // always within reach on long pages — the inner nav scrolls on its own.
        style={{
          position: "sticky",
          top: 0,
          height: "100vh",
          alignSelf: "flex-start",
          background: token.colorBgContainer,
          borderRight: `1px solid ${token.colorBorderSecondary}`,
          overflow: "hidden",
          transition: "all 200ms ease",
        }}
      >
        <div
          style={{
            position: "relative",
            height: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div style={{ flex: "1 1 auto", minHeight: 0 }}>
            <SidebarContent onNavigate={() => {}} />
          </div>
          <div
            style={{
              flex: "0 0 auto",
              display: "flex",
              justifyContent: "flex-end",
              padding: spacing.xs,
              borderTop: `1px solid ${token.colorBorderSecondary}`,
            }}
          >
            <Tooltip title="Collapse to rail" placement="right">
              <Button
                type="text"
                icon={<MenuFoldOutlined />}
                onClick={toggleExpanded}
                aria-label="Collapse sidebar"
                style={{ height: 40 }}
              />
            </Tooltip>
          </div>
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
          height: "100vh",
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

        {/* Chat */}
        {canChat && (
          <RailButton
            label="Chat"
            icon={<MessageOutlined />}
            active={flyout === "chat"}
            stopsMouseDown
            onClick={() => toggleFlyout("chat")}
          />
        )}

        {/* Spacer */}
        <div style={{ flex: "1 1 auto" }} />

        {/* Account */}
        <RailButton
          label="Account"
          icon={<UserOutlined />}
          active={flyout === "account"}
          stopsMouseDown
          onClick={() => toggleFlyout("account")}
        />

        {/* Expand chevron */}
        <Tooltip title="Expand sidebar" placement="right">
          <Button
            type="text"
            aria-label="Expand sidebar"
            onClick={toggleExpanded}
            style={{
              height: 44,
              width: RAIL_WIDTH,
              borderRadius: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: token.colorTextSecondary,
            }}
            icon={
              <span
                style={{ fontSize: token.fontSizeLG, display: "inline-flex" }}
              >
                <RightOutlined />
              </span>
            }
          />
        </Tooltip>
      </div>

      {/* Flyout panel — reads `flyout` from the store itself. */}
      <SidebarFlyout />
    </>
  );
}
