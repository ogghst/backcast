/**
 * ChatSlimHeader
 *
 * The ONE collapsible header for the dedicated chat shell. Sibling chrome of
 * `AppLayout`'s header but slimmer and borderless-bottom.
 *
 * Layout (left → right):
 *   [Back] [Brand] [ContextLabel] ......... (expanded-only chat actions) [NotificationBell] [UserProfile]
 *
 * Collapse behaviour:
 *   - Collapsed by default (~48px): always-visible row only.
 *   - Expands (~96px) on hover (with a ~180ms grace delay to avoid jitter) OR
 *     on click of the chevron affordance. Reveals the portaled chat controls.
 *   - Collapses on mouse-leave (after the grace delay) or on Escape.
 *   - `transition: height 200ms ease` on the wrapper.
 *
 * Back button: `navigate(state.returnTo ?? -1)`. Falls back to `/` when there is
 * no router history (history.length <= 1) to avoid a no-op.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Button, Space, Tooltip, Grid, theme } from "antd";
import {
  ArrowLeftOutlined,
  RobotOutlined,
  DownOutlined,
  UpOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";

import { UserProfile } from "@/components/UserProfile";
import { NotificationBell } from "@/features/notifications";
import { useChatContextFromUrl } from "@/hooks/navigation/useChatContextFromUrl";

const { useBreakpoint } = Grid;

/** Instant, static label for the active chat context (entity name is resolved lazily). */
function contextLabel(ctxType: string): string {
  switch (ctxType) {
    case "project":
      return "Project chat";
    case "wbe":
      return "WBS Element chat";
    case "cost_element":
      return "Cost Element chat";
    case "work_package":
      return "Work Package chat";
    default:
      return "General chat";
  }
}

interface ChatSlimHeaderProps {
  /**
   * Ref callback that receives the actions-container DOM node. `ChatLayout`
   * stores it as the portal TARGET so `ChatInterface` can render its controls
   * into this region. The whole container is hidden when collapsed, so the
   * portaled controls hide with it.
   */
  actionsRef?: (el: HTMLElement | null) => void;
}

export const ChatSlimHeader: React.FC<ChatSlimHeaderProps> = ({ actionsRef }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const screens = useBreakpoint();
  const isMd = !!screens.md;
  const {
    token: {
      colorBgContainer,
      colorPrimary,
      colorTextSecondary,
      colorBorderSecondary,
      paddingSM,
      paddingXS,
      fontSizeLG,
      fontSizeSM,
      boxShadowSecondary,
    },
  } = theme.useToken();

  const { context } = useChatContextFromUrl();

  const [isExpanded, setIsExpanded] = useState(false);
  const graceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearGrace = useCallback(() => {
    if (graceTimer.current) {
      clearTimeout(graceTimer.current);
      graceTimer.current = null;
    }
  }, []);

  const scheduleExpand = useCallback(() => {
    clearGrace();
    setIsExpanded(true);
  }, [clearGrace]);

  const scheduleCollapse = useCallback(() => {
    clearGrace();
    // Grace delay avoids jitter when the pointer transits between the header
    // and a child dropdown/popover anchored just below it.
    graceTimer.current = setTimeout(() => setIsExpanded(false), 180);
  }, [clearGrace]);

  const toggleExpanded = useCallback(() => {
    clearGrace();
    setIsExpanded((prev) => !prev);
  }, [clearGrace]);

  // Collapse on Escape + cleanup the grace timer on unmount.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        clearGrace();
        setIsExpanded(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      clearGrace();
    };
  }, [clearGrace]);

  const handleBack = useCallback(() => {
    const state = location.state as { returnTo?: string } | null;
    const returnTo = state?.returnTo;
    if (returnTo) {
      navigate(returnTo);
      return;
    }
    // No explicit return target: walk back in history if there is any, else go home.
    if (typeof window !== "undefined" && window.history.length > 1) {
      navigate(-1);
    } else {
      navigate("/");
    }
  }, [location.state, navigate]);

  const collapsedHeight = 48;
  // The expanded row holds the portaled chat controls (assistant selector, new
  // chat, debug, sidebar/menu toggles — ≥44px touch targets on mobile). The old
  // 64px total left only 16px for this row, clipping the controls. Size it to fit.
  const actionsRowHeight = 48;
  const expandedHeight = collapsedHeight + actionsRowHeight;

  return (
    <header
      role="banner"
      onMouseEnter={scheduleExpand}
      onMouseLeave={scheduleCollapse}
      style={{
        position: "sticky",
        top: 0,
        zIndex: 20,
        height: isExpanded ? expandedHeight : collapsedHeight,
        transition: "height 200ms ease",
        background: colorBgContainer,
        borderBottom: isExpanded
          ? `1px solid ${colorBorderSecondary}`
          : "1px solid transparent",
        boxShadow: isExpanded ? boxShadowSecondary : "none",
        overflow: "hidden",
      }}
    >
      {/* Always-visible row (collapsed state) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: paddingSM,
          height: collapsedHeight,
          padding: `0 ${isMd ? paddingSM : paddingXS}px`,
        }}
      >
        <Tooltip title="Back">
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={handleBack}
            aria-label="Back"
            style={{ display: "inline-flex", alignItems: "center" }}
          />
        </Tooltip>

        <Space size={paddingXS} align="center" style={{ lineHeight: 1 }}>
          <RobotOutlined style={{ color: colorPrimary, fontSize: fontSizeLG }} />
          {isMd && (
            <span
              style={{
                fontWeight: 600,
                fontSize: fontSizeLG,
                color: colorPrimary,
                whiteSpace: "nowrap",
              }}
            >
              Backcast
            </span>
          )}
          {isMd && (
            <span
              style={{
                fontSize: fontSizeSM,
                color: colorTextSecondary,
                whiteSpace: "nowrap",
              }}
            >
              {contextLabel(context.type)}
            </span>
          )}
        </Space>

        <div style={{ flex: 1 }} />

        {/* Expanded-only chat actions are rendered below this row (see actionsRow).
            A chevron toggles expansion for keyboard/click users. */}
        <Tooltip title={isExpanded ? "Collapse header" : "Expand header"}>
          <Button
            type="text"
            size="small"
            icon={isExpanded ? <UpOutlined /> : <DownOutlined />}
            onClick={toggleExpanded}
            aria-label={isExpanded ? "Collapse header" : "Expand header"}
            aria-expanded={isExpanded}
            style={{ display: "inline-flex", alignItems: "center" }}
          />
        </Tooltip>

        <Space size={paddingXS} align="center">
          <NotificationBell />
          <UserProfile />
        </Space>
      </div>

      {/* Expanded-only chat actions row. ChatInterface portals its controls into
          this container via the ref callback; the container is hidden when
          collapsed so the portaled controls hide with it. */}
      <div
        ref={actionsRef}
        style={{
          display: isExpanded ? "flex" : "none",
          alignItems: "center",
          gap: paddingSM,
          height: actionsRowHeight,
          padding: `0 ${isMd ? paddingSM : paddingXS}px`,
        }}
      />
    </header>
  );
};
