/**
 * Rail-mode inline flyout panel.
 *
 * Shown when `useNavigationStore.flyout !== null` in DESKTOP rail mode only
 * (`AppSidebar` forces flyout to null while expanded). Renders an overlay panel
 * flush against the 56px rail (absolute, left: 56px) carrying the selected
 * content section:
 *
 *   - "account"→ account menu (reuses `useAccountMenuItems`)
 *   - "entity" → entity nav items (reuses `useEntityNav`)
 *
 * a11y: `aria-modal`, focus moves into the panel on open, Escape + outside
 * click close it. After a destination navigation it also closes.
 *
 * z-index: the flyout sits ABOVE ordinary page content but BELOW modals,
 * TimeMachine, and the mobile Drawer. antd's `zIndexPopupBase` is 1000 —
 * modals/drawers pop at that tier. The flyout uses 900 so any modal/TM opened
 * on top (e.g. the global close-on-TM-expand effect) always wins. This is read
 * off the token so a custom theme still wins.
 */

import { useCallback, useEffect, useRef } from "react";
import { Menu, Typography, theme } from "antd";
import { useLocation, useNavigate } from "react-router-dom";

import { useAccountMenuItems } from "@/components/navigation/accountMenuItems";
import { useEntityNav } from "@/components/navigation/useEntityNav";
import type { NavFlyout } from "@/stores/useNavigationStore";
import { useNavigationStore } from "@/stores/useNavigationStore";
import { useThemeTokens } from "@/hooks/useThemeTokens";

const { Text } = Typography;

const RAIL_WIDTH = 56;
const FLYOUT_WIDTH = 288;

// antd's default `zIndexPopupBase` is 1000 (modals / drawers / popups). The
// flyout must sit below that tier so any modal/TimeMachine opened over it
// always wins. 900 is comfortably above normal content while staying under the
// popup tier; read from the token in case a custom theme changes the base.
function useFlyoutZIndex(): number {
  const { token } = theme.useToken();
  const base =
    (token as typeof token & { zIndexPopupBase?: number }).zIndexPopupBase ??
    1000;
  // Use base - 100 so the popup tier (base) always wins. Floor at 100 so a
  // misconfigured theme can't sink the flyout under page content.
  return Math.max(100, base - 100);
}

function AccountPanel({ onClose }: { onClose: () => void }) {
  const accountItems = useAccountMenuItems();
  const location = useLocation();

  return (
    <Menu
      mode="inline"
      items={accountItems}
      selectedKeys={[location.pathname]}
      // The account items embed their own onClick navigations; closing the
      // flyout afterwards keeps the rail tidy.
      onClick={onClose}
      style={{ border: "none", background: "transparent" }}
    />
  );
}

function EntityPanel({ onClose }: { onClose: () => void }) {
  const { token } = theme.useToken();
  const { spacing } = useThemeTokens();
  const entityNav = useEntityNav();
  const navigate = useNavigate();
  const location = useLocation();

  if (!entityNav) {
    return (
      <div style={{ padding: spacing.md }}>
        <Text type="secondary">No entity on this route.</Text>
      </div>
    );
  }

  return (
    <div>
      <div style={{ padding: `${spacing.xs}px ${spacing.md}px` }}>
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
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        // Unlike the account panel (whose items embed their own onClick
        // navigations), the entity nav items are pure { key, label, path } with
        // no handler. Each item's Menu key IS its path, so navigate on the
        // Menu-level click, then close the flyout.
        onClick={(info) => {
          navigate(info.key);
          onClose();
        }}
        items={entityNav.items.map((i) => ({
          key: i.path,
          label: i.label,
        }))}
        style={{ border: "none", background: "transparent" }}
      />
    </div>
  );
}

function panelContent(flyout: Exclude<NavFlyout, null>, onClose: () => void) {
  switch (flyout) {
    case "account":
      return <AccountPanel onClose={onClose} />;
    case "entity":
      return <EntityPanel onClose={onClose} />;
  }
}

export function SidebarFlyout(): React.JSX.Element | null {
  const { token } = theme.useToken();
  const flyout = useNavigationStore((s) => s.flyout);
  const setFlyout = useNavigationStore((s) => s.setFlyout);
  const zIndex = useFlyoutZIndex();

  const panelRef = useRef<HTMLDivElement>(null);
  // The element that had focus before the flyout opened — focus is restored to
  // it on close (the opener rail button), matching modal dialog behavior.
  const triggerRef = useRef<HTMLElement | null>(null);

  const close = useCallback(() => setFlyout(null), [setFlyout]);

  // Escape closes the flyout.
  useEffect(() => {
    if (flyout === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [flyout, close]);

  // Outside click closes; focus moves into the panel on open; Tab is wrapped
  // within the panel (focus trap); focus is restored to the opener on close.
  useEffect(() => {
    if (flyout === null) return;

    // Capture the opener so focus can be returned on close.
    triggerRef.current = document.activeElement as HTMLElement | null;

    const onPointerDown = (e: MouseEvent) => {
      const panel = panelRef.current;
      if (panel && !panel.contains(e.target as Node)) {
        close();
      }
    };
    document.addEventListener("mousedown", onPointerDown);

    // Focus trap: on Tab/Shift+Tab, wrap focus within the panel.
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const panel = panelRef.current;
      if (!panel) return;
      const focusable = panel.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) {
        // No focusable children — keep focus on the panel itself.
        e.preventDefault();
        panel.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey) {
        if (active === first || active === panel || !panel.contains(active)) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (active === last || !panel.contains(active)) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKeyDown);

    // Move focus into the panel on open.
    const t = window.setTimeout(() => {
      panelRef.current?.focus();
    }, 0);

    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
      window.clearTimeout(t);
      // Restore focus to the opener.
      triggerRef.current?.focus?.();
      triggerRef.current = null;
    };
  }, [flyout, close]);

  if (flyout === null) return null;

  return (
    <div
      ref={panelRef}
      role="dialog"
      aria-modal="true"
      aria-label={`${flyout} panel`}
      tabIndex={-1}
      style={{
        position: "absolute",
        top: 0,
        left: RAIL_WIDTH,
        width: FLYOUT_WIDTH,
        height: "100%",
        background: token.colorBgContainer,
        boxShadow: token.boxShadowSecondary,
        borderRight: `1px solid ${token.colorBorderSecondary}`,
        zIndex,
        display: "flex",
        flexDirection: "column",
        overflow: "auto",
        outline: "none",
      }}
    >
      {panelContent(flyout, close)}
    </div>
  );
}
