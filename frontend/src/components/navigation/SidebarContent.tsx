/**
 * Shared full-width sidebar body.
 *
 * Used by BOTH the expanded desktop `AppSidebar` and the `MobileSidebarDrawer`
 * (DRY — one layout, two hosts). Renders, top → bottom:
 *   1. Brand wordmark + glyph (clickable → `/`).
 *   2. Primary nav (Dashboard, Projects) with active highlighting.
 *   3. Entity section (only when `useEntityNav()` is non-null) — a static label
 *      heading + the route-derived nav items, indented under primary nav.
 *   4. Chat (gated `ai-chat`) — a primary nav row that navigates to `/chat`
 *      AND carries a trailing chevron that toggles a chat-history list
 *      (collapsed by default each mount). The history list is
 *      React.lazy-imported so chat deps stay code-split.
 *   5. Admin (gated `hasRole("admin")`) — a collapsible section header (NOT a
 *      navigator; there is no `/admin` index route) whose trailing chevron
 *      toggles the permission-gated admin-page list (`useAdminNavItems`).
 *      Collapsed by default each mount. Sub-items navigate via `go()`.
 *   6. Account section (bottom) — user avatar + name + role and the shared
 *      RBAC-gated account menu (`useAccountMenuItems`).
 *
 * All styling uses Ant Design theme tokens (zero hard-coded colors). Hover and
 * active states use `token.colorBgTextHover` / `token.colorPrimaryBg`.
 */

import { Suspense, lazy, useState } from "react";
import {
  Avatar,
  Badge,
  Divider,
  Dropdown,
  Spin,
  Typography,
  theme,
} from "antd";
import {
  AppstoreOutlined,
  DownOutlined,
  HomeOutlined,
  MessageOutlined,
  RightOutlined,
  RobotOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";

import { Can } from "@/components/auth/Can";
import {
  useAccountMenuItems,
} from "@/components/navigation/accountMenuItems";
import { useAdminNavItems } from "@/components/navigation/adminNavItems";
import { useEntityNav } from "@/components/navigation/useEntityNav";
import type { NavigationItem } from "@/components/navigation";
import { serializeCtx } from "@/hooks/navigation/useChatContextFromUrl";
import { useEffectiveChatContext } from "@/hooks/navigation/useEffectiveChatContext";
import { useRunningExecutionsCount } from "@/features/ai/chat/api/useAgentExecutions";
import { useAuth } from "@/hooks/useAuth";
import { usePermission } from "@/hooks/usePermission";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import type { SessionContext } from "@/features/ai/types";

// Code-split the chat feature out of the sidebar chunk.
const SidebarChatHistory = lazy(() =>
  import("@/components/navigation/SidebarChatHistory").then((m) => ({
    default: m.default,
  })),
);

const { Text } = Typography;

interface PrimaryNavItem {
  key: string;
  label: string;
  path: string;
  icon: React.ReactNode;
}

const PRIMARY_NAV: PrimaryNavItem[] = [
  { key: "dashboard", label: "Dashboard", path: "/", icon: <HomeOutlined /> },
  {
    key: "projects",
    label: "Projects",
    path: "/projects",
    icon: <AppstoreOutlined />,
  },
];

interface SidebarContentProps {
  /**
   * Called after a primary/entity nav item is clicked. Used by hosts that need
   * to dismiss an overlay (mobile drawer, rail flyout) on navigation. Default
   * no-op for the always-expanded desktop sider.
   */
  onNavigate?: () => void;
}

/**
 * Is `path` the active route? Dashboard (`/`) is matched exactly; everything
 * else uses startsWith so sub-routes (e.g. `/projects/123/dashboard`) keep the
 * parent highlighted appropriately. Entity-item matching is exact (handled by
 * the entity list below).
 */
function isPrimaryActive(pathname: string, path: string): boolean {
  if (path === "/") return pathname === "/";
  return pathname === path || pathname.startsWith(`${path}/`);
}

/**
 * Inline primary nav row. Used instead of antd `Menu` to keep full control of
 * the row height (≥44px touch target), active highlight, and hover treatment
 * with theme tokens.
 */
function NavRow({
  item,
  active,
  onClick,
  indent,
  trailing,
  badge,
}: {
  item: PrimaryNavItem | NavigationItem;
  active: boolean;
  onClick: () => void;
  indent: number;
  trailing?: React.ReactNode;
  badge?: React.ReactNode;
}) {
  const { token } = theme.useToken();
  const { spacing, borderRadius, typography } = useThemeTokens();
  const icon = "icon" in item && item.icon ? item.icon : null;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      style={{
        display: "flex",
        alignItems: "center",
        gap: spacing.sm + 2,
        minHeight: 44, // ≥44px touch target
        padding: `${spacing.sm}px ${spacing.md}px`,
        marginLeft: indent,
        marginRight: spacing.xs,
        marginTop: 2,
        marginBottom: 2,
        borderRadius: borderRadius.md,
        cursor: "pointer",
        color: active ? token.colorPrimary : token.colorText,
        background: active ? token.colorPrimaryBg : "transparent",
        fontWeight: active
          ? typography.weights.semiBold
          : typography.weights.normal,
        borderLeft: active
          ? `3px solid ${token.colorPrimary}`
          : "3px solid transparent",
        transition: "background-color 120ms ease, color 120ms ease",
      }}
      onMouseEnter={(e) => {
        if (!active) e.currentTarget.style.background = token.colorBgTextHover;
      }}
      onMouseLeave={(e) => {
        if (!active) e.currentTarget.style.background = "transparent";
      }}
    >
      {icon && (
        <span style={{ fontSize: token.fontSizeLG, display: "inline-flex" }}>
          {icon}
        </span>
      )}
      <span
        style={{
          fontSize: token.fontSize,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          ...(trailing
            ? { flex: 1, minWidth: 0 }
            : undefined),
        }}
      >
        {item.label}
      </span>
      {badge && <span style={{ display: "inline-flex", alignItems: "center" }}>{badge}</span>}
      {trailing && (
        <span
          style={{
            marginLeft: "auto",
            flexShrink: 0,
            display: "inline-flex",
            alignItems: "center",
          }}
        >
          {trailing}
        </span>
      )}
    </div>
  );
}

/**
 * Open the chat page directly. No-op when already on /chat so an active
 * conversation isn't reset. The current effective context is serialized into
 * the `?ctx=` URL contract so project/scope is preserved across the nav.
 * returnTo lets the in-chat Back button return here. Mirrors
 * `AppSidebar.handleChatNav` so rail and expanded behave identically.
 */
function useChatNav(
  navigate: (path: string, opts?: { state?: unknown }) => void,
  pathname: string,
  search: string,
  ctx: SessionContext,
  onNavigate?: () => void,
) {
  return () => {
    if (pathname === "/chat") return;
    navigate(`/chat?${serializeCtx(ctx)}`, {
      state: { returnTo: pathname + search },
    });
    onNavigate?.();
  };
}

export function SidebarContent({
  onNavigate,
}: SidebarContentProps): React.JSX.Element {
  const { token } = theme.useToken();
  const { spacing, borderRadius } = useThemeTokens();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  // Chat history is collapsed by default; the Chat nav row carries a chevron
  // that toggles this. Not persisted — collapses again on each sidebar mount.
  const [chatHistoryOpen, setChatHistoryOpen] = useState(false);

  // Admin section is collapsed by default; its header (a NavRow, NOT a
  // navigator) toggles this. Not persisted — collapses on each sidebar mount.
  const [adminOpen, setAdminOpen] = useState(false);

  const effectiveCtx = useEffectiveChatContext();
  const { can, canAny, hasRole } = usePermission();
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
  // Section-level gate: admin role AND at least one visible item. Per-item
  // gating lives in `useAdminNavItems`; the section-level admin-role guard
  // lives here (the hook does not enforce it).
  const showAdmin = hasRole("admin") && adminItems.length > 0;

  const entityNav = useEntityNav();
  const accountItems = useAccountMenuItems({ includeUserInfo: false });

  const handleChatNav = useChatNav(
    navigate,
    location.pathname,
    location.search,
    effectiveCtx,
    onNavigate,
  );

  const go = (path: string) => {
    navigate(path);
    onNavigate?.();
  };

  const initials = (user?.full_name || user?.email || "U")
    .split(/\s+/)
    .map((s) => s[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <nav
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: token.colorBgContainer,
        borderRight: `1px solid ${token.colorBorderSecondary}`,
        overflow: "hidden",
      }}
      aria-label="Primary"
    >
      {/* Scrollable region: brand, primary nav, entity nav, chat. Scrolls on
          its own when chat is expanded so the account footer below stays put. */}
      <div
        style={{
          flex: "1 1 auto",
          minHeight: 0,
          overflowY: "auto",
          overflowX: "hidden",
        }}
      >
      {/* Brand */}
      <button
        type="button"
        onClick={() => go("/")}
        style={{
          display: "flex",
          alignItems: "center",
          gap: spacing.sm + 2,
          padding: `${spacing.md}px ${spacing.lg}px`,
          minHeight: 56,
          background: "transparent",
          border: "none",
          cursor: "pointer",
          width: "100%",
          textAlign: "left",
        }}
        aria-label="Backcast home"
      >
        <ThunderboltOutlined
          style={{ color: token.colorPrimary, fontSize: token.fontSizeXL }}
        />
        <Text
          strong
          style={{
            color: token.colorPrimary,
            fontSize: token.fontSizeXL,
            fontFamily: token.fontFamily,
            whiteSpace: "nowrap",
          }}
        >
          Backcast
        </Text>
      </button>

      {/* Primary nav */}
      <div style={{ flex: "0 0 auto" }}>
        {PRIMARY_NAV.map((item) => (
          <NavRow
            key={item.key}
            item={item}
            active={isPrimaryActive(location.pathname, item.path)}
            onClick={() => go(item.path)}
            indent={spacing.xs}
          />
        ))}
      </div>

      {/* Entity section (only on entity-detail routes) */}
      {entityNav && (
        <>
          <Divider
            style={{
              margin: `${spacing.sm}px ${spacing.md}px`,
              borderColor: token.colorBorderSecondary,
            }}
          />
          <div style={{ flex: "0 0 auto" }}>
            <div style={{ padding: `${spacing.xs}px ${spacing.lg}px` }}>
              <Text
                type="secondary"
                style={{
                  fontSize: token.fontSizeSM,
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                }}
              >
                {entityNav.label}
              </Text>
            </div>
            {entityNav.items.map((item) => (
              <NavRow
                key={item.key}
                item={item}
                active={location.pathname === item.path}
                onClick={() => go(item.path)}
                indent={spacing.md}
              />
            ))}
          </div>
        </>
      )}

      {/* Chat — a primary nav row that navigates to /chat AND carries a
          trailing chevron that toggles the chat-history list below it. The
          history list is collapsed by default each mount (the chevron's
          onClick/ onKeyDown call stopPropagation so toggling does NOT trigger
          the row's navigation). No section header: the SessionList renders its
          own affordances. */}
      <Can permission="ai-chat">
        <Divider
          style={{
            margin: `${spacing.sm}px ${spacing.md}px`,
            borderColor: token.colorBorderSecondary,
          }}
        />
        <NavRow
          item={{
            key: "chat",
            label: "Chat",
            path: "/chat",
            icon: <MessageOutlined />,
          }}
          active={isPrimaryActive(location.pathname, "/chat")}
          onClick={handleChatNav}
          indent={spacing.xs}
          trailing={
            <span
              role="button"
              tabIndex={0}
              aria-label={
                chatHistoryOpen
                  ? "Collapse chat history"
                  : "Expand chat history"
              }
              aria-expanded={chatHistoryOpen}
              onClick={(e) => {
                e.stopPropagation();
                setChatHistoryOpen((open) => !open);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  e.stopPropagation();
                  setChatHistoryOpen((open) => !open);
                }
              }}
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 24,
                height: 24,
                borderRadius: borderRadius.sm,
                color: token.colorTextSecondary,
                cursor: "pointer",
              }}
            >
              {chatHistoryOpen ? <DownOutlined /> : <RightOutlined />}
            </span>
          }
        />
        {chatHistoryOpen && (
          <div style={{ flex: "0 0 auto" }}>
            <Suspense
              fallback={
                <div
                  style={{
                    display: "flex",
                    justifyContent: "center",
                    padding: spacing.lg,
                  }}
                >
                  <Spin />
                </div>
              }
            >
              <SidebarChatHistory />
            </Suspense>
          </div>
        )}
      </Can>

      {/* Agents — a single nav row directly below Chat. Managers
          (agent-schedule-manage) land on Schedules; chat-only users land on
          History. Badged with the running-executions count. Active on either
          destination route. */}
      <Can permission={["ai-chat", "agent-schedule-manage"]}>
        <Divider
          style={{
            margin: `${spacing.sm}px ${spacing.md}px`,
            borderColor: token.colorBorderSecondary,
          }}
        />
        <NavRow
          item={{
            key: "agents",
            label: "Agents",
            path: agentsDest,
            icon: <RobotOutlined />,
          }}
          active={agentsActive}
          onClick={() => go(agentsDest)}
          indent={spacing.xs}
          badge={runningCount > 0 ? <Badge count={runningCount} size="small" /> : undefined}
        />
      </Can>

      {/* Admin — admin-gated collapsible section, collapsed by default. The
          header NavRow TOGGLES (it does NOT navigate: there is no `/admin`
          index route). The trailing chevron is a pure visual indicator; clicks
          bubble up to the row and toggle (NO stopPropagation — unlike the Chat
          chevron, where the row navigates and the chevron must suppress nav).
          Sub-items are permission-gated admin pages (`useAdminNavItems`) and
          navigate via `go()`. */}
      {showAdmin && (
        <>
          <Divider
            style={{
              margin: `${spacing.sm}px ${spacing.md}px`,
              borderColor: token.colorBorderSecondary,
            }}
          />
          <NavRow
            item={{
              key: "admin",
              label: "Admin",
              path: "/admin",
              icon: <SettingOutlined />,
            }}
            active={location.pathname.startsWith("/admin")}
            onClick={() => setAdminOpen((open) => !open)}
            indent={spacing.xs}
            trailing={adminOpen ? <DownOutlined /> : <RightOutlined />}
          />
          {adminOpen && (
            <div style={{ flex: "0 0 auto" }}>
              {adminItems.map((item) => (
                <NavRow
                  key={item.key}
                  item={item}
                  active={location.pathname === item.path}
                  onClick={() => go(item.path)}
                  indent={spacing.md}
                />
              ))}
            </div>
          )}
        </>
      )}
      </div>

      {/* Account footer — pinned at the bottom, OUTSIDE the scroll region, so
          the avatar is always visible. Click opens the account menu as a
          dropdown (no chevron: the sidebar expands only via the Expand button). */}
      <div
        style={{
          flex: "0 0 auto",
          borderTop: `1px solid ${token.colorBorderSecondary}`,
        }}
      >
        <Dropdown menu={{ items: accountItems }} trigger={["click"]} placement="top">
          <div
            role="button"
            tabIndex={0}
            aria-label="Account menu"
            style={{
              display: "flex",
              alignItems: "center",
              gap: spacing.sm,
              minHeight: 44,
              padding: `${spacing.sm}px ${spacing.md}px`,
              cursor: "pointer",
              transition: "background-color 120ms ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = token.colorBgTextHover;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
          >
            <Avatar
              size={32}
              icon={<UserOutlined />}
              style={{ backgroundColor: token.colorPrimary, flexShrink: 0 }}
            >
              {initials}
            </Avatar>
            <div style={{ minWidth: 0, flex: 1 }}>
              <Text strong ellipsis style={{ display: "block", fontSize: token.fontSize }}>
                {user?.full_name || "User"}
              </Text>
              <Text
                type="secondary"
                style={{ fontSize: token.fontSizeSM, textTransform: "capitalize" }}
              >
                {user?.role || "viewer"}
              </Text>
            </div>
          </div>
        </Dropdown>
      </div>
    </nav>
  );
}
