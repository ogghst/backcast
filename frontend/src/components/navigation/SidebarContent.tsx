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
 *      followed by the always-visible chat-history list (sessions + new chat).
 *      The history list is React.lazy-imported so chat deps stay code-split.
 *   5. Account section (bottom) — user avatar + name + role and the shared
 *      RBAC-gated account menu (`useAccountMenuItems`).
 *
 * All styling uses Ant Design theme tokens (zero hard-coded colors). Hover and
 * active states use `token.colorBgTextHover` / `token.colorPrimaryBg`.
 */

import { Suspense, lazy } from "react";
import {
  Avatar,
  Divider,
  Dropdown,
  Spin,
  Typography,
  theme,
} from "antd";
import {
  AppstoreOutlined,
  HomeOutlined,
  MessageOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";

import { Can } from "@/components/auth/Can";
import {
  useAccountMenuItems,
} from "@/components/navigation/accountMenuItems";
import { useEntityNav } from "@/components/navigation/useEntityNav";
import type { NavigationItem } from "@/components/navigation";
import { serializeCtx } from "@/hooks/navigation/useChatContextFromUrl";
import { useEffectiveChatContext } from "@/hooks/navigation/useEffectiveChatContext";
import { useAuth } from "@/hooks/useAuth";
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
}: {
  item: PrimaryNavItem | NavigationItem;
  active: boolean;
  onClick: () => void;
  indent: number;
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
        }}
      >
        {item.label}
      </span>
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
  const { spacing } = useThemeTokens();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  const effectiveCtx = useEffectiveChatContext();

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

      {/* Chat — a primary nav row that navigates to /chat (NOT a toggle),
          followed by the always-visible chat-history list (sessions + the
          SessionList "New Chat" button). No section header: the SessionList
          renders its own affordances, so a redundant "Chat history" label is
          unnecessary. */}
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
        />
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
      </Can>
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
