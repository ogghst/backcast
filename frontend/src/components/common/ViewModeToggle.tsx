import { Button, Tooltip } from "antd";
import { AppstoreOutlined, TableOutlined, DesktopOutlined } from "@ant-design/icons";
import type { ViewMode } from "@/hooks/useViewMode";

interface ViewModeToggleProps {
  viewMode: ViewMode;
  onCycleViewMode: () => void;
}

export const ViewModeToggle = ({ viewMode, onCycleViewMode }: ViewModeToggleProps) => {
  const tooltipText = viewMode === "table" ? "Switch to card" : viewMode === "card" ? "Switch to auto" : "Switch to table";
  const icon = viewMode === "table" ? <TableOutlined /> : viewMode === "card" ? <AppstoreOutlined /> : <DesktopOutlined />;

  return (
    <Tooltip title={tooltipText}>
      <Button type="text" icon={icon} onClick={onCycleViewMode} />
    </Tooltip>
  );
};
