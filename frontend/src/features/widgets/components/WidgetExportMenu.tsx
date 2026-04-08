import { Button, Dropdown } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import type { MenuProps } from "antd";
import {
  exportChartAsPNG,
  exportTableAsCSV,
  exportJSON,
  buildExportFilename,
} from "../utils/exportUtils";

interface ChartLike {
  getDataURL: (opts: {
    type: string;
    pixelRatio: number;
    backgroundColor: string;
  }) => string;
}

interface WidgetExportMenuProps {
  widgetType: string;
  dashboardName: string;
  getChartInstance?: (() => ChartLike | null) | undefined;
  getTableData?:
    | (() => { columns: string[]; rows: string[][] })
    | undefined;
  getRawData?: (() => unknown) | undefined;
}

export function WidgetExportMenu({
  widgetType,
  dashboardName,
  getChartInstance,
  getTableData,
  getRawData,
}: WidgetExportMenuProps) {
  const handleExportPNG = () => {
    const chart = getChartInstance?.();
    if (chart) {
      exportChartAsPNG(
        chart,
        buildExportFilename(widgetType, dashboardName, "png"),
      );
    }
  };

  const handleExportCSV = () => {
    const tableData = getTableData?.();
    if (tableData) {
      exportTableAsCSV(
        tableData.columns,
        tableData.rows,
        buildExportFilename(widgetType, dashboardName, "csv"),
      );
    }
  };

  const handleExportJSON = () => {
    const data = getRawData?.();
    if (data !== undefined) {
      exportJSON(data, buildExportFilename(widgetType, dashboardName, "json"));
    }
  };

  const items: MenuProps["items"] = [
    {
      key: "png",
      label: "Export as PNG",
      disabled: !getChartInstance,
      onClick: handleExportPNG,
    },
    {
      key: "csv",
      label: "Export as CSV",
      disabled: !getTableData,
      onClick: handleExportCSV,
    },
    {
      key: "json",
      label: "Export as JSON",
      disabled: !getRawData,
      onClick: handleExportJSON,
    },
  ];

  return (
    <Dropdown menu={{ items }} trigger={["click"]}>
      <Button
        type="text"
        size="small"
        icon={<DownloadOutlined />}
        title="Export widget data"
        onPointerDown={(e) => e.stopPropagation()}
      />
    </Dropdown>
  );
}
