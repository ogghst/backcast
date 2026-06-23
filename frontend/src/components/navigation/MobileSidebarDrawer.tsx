/**
 * Mobile off-canvas sidebar drawer.
 *
 * Renders the full `SidebarContent` inside an antd left-anchored `Drawer`.
 * antd owns focus management + Escape + backdrop scrim, so this is a thin
 * shell that binds `open` to `useNavigationStore.mobileOpen` and dismisses on
 * navigation (via `SidebarContent.onNavigate`).
 *
 * Rendered at the AppLayout root in Phase 2 (this phase only builds it).
 */

import { Drawer, Grid } from "antd";

import { SidebarContent } from "@/components/navigation/SidebarContent";
import { useNavigationStore } from "@/stores/useNavigationStore";

/**
 * On very small phones (< sm breakpoint ≈ 576px) use a percentage width so the
 * drawer never overflows the viewport; otherwise a comfortable fixed 280px.
 */
export function MobileSidebarDrawer(): React.JSX.Element {
  const screens = Grid.useBreakpoint();
  const mobileOpen = useNavigationStore((s) => s.mobileOpen);
  const setMobileOpen = useNavigationStore((s) => s.setMobileOpen);

  const width: string | number = screens.sm ? 280 : "85%";

  return (
    <Drawer
      placement="left"
      open={mobileOpen}
      onClose={() => setMobileOpen(false)}
      width={width}
      // No body padding — SidebarContent owns its own spacing.
      styles={{ body: { padding: 0 } }}
      // Keep the drawer below the popup tier so chat/modals opened from it
      // still appear above the scrim.
      zIndex={1000}
    >
      <SidebarContent onNavigate={() => setMobileOpen(false)} />
    </Drawer>
  );
}
