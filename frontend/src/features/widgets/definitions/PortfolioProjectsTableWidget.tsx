/**
 * Portfolio Projects table widget — per-project EVM breakdown.
 *
 * Phase 4 of the global-dashboard-widgets initiative. Ports the `renderTable`
 * section of the legacy `PortfolioPage.tsx` (~L358-485, ~L574-592) — the
 * client-side status+RAG filter, the column set, and the config-driven default
 * sort — into a self-registering widget wrapped in `WidgetShell`.
 *
 * LOCKED constraints (design doc §5.2, G16/G17):
 *  - Branch FROZEN to `main`/`merged` (G16). NEVER reads `ctx.branch`/`ctx.mode`.
 *  - Reads status / rag / controlDate from `ctx.portfolioFilter` (NOT the
 *    `usePortfolioFilterStore` directly). When the host (Phase 8) has not
 *    populated `portfolioFilter`, all filters are null → unfiltered (today/main).
 *
 * `defaultConfig.defaultSort` replaces the legacy `roleLayout.defaultSort`; URL
 * sort still wins (the user's active sort takes precedence on reload).
 *
 * Source design: docs/03-project-plan/iterations/2026-06-29-global-dashboard-widgets/
 *   global-dashboard-widgets-design.md §5.2 (portfolio-projects-table) + §7 Phase 4.
 */

import { TableOutlined } from "@ant-design/icons";
import { Tag } from "antd";
import type { ColumnType } from "antd/es/table";
import type { SortOrder } from "antd/es/table/interface";
import { Link } from "react-router-dom";
import { useMemo } from "react";
import type { FC } from "react";
import { useDashboardContext } from "../context/useDashboardContext";
import { usePortfolioEVM } from "@/features/portfolio/api/usePortfolioEVM";
import { useTableParams } from "@/hooks/useTableParams";
import { StandardTable } from "@/components/common/StandardTable";
import { formatValue } from "@/features/evm/utils/formatters";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";
import type { PortfolioProjectMetrics } from "@/api/generated/models/PortfolioProjectMetrics";
import { ragBand, type RagBand } from "./shared/portfolioMetrics";

interface PortfolioProjectsTableConfig {
  defaultSortField?:
    | "cpi"
    | "spi"
    | "name"
    | "status"
    | "vac"
    | "contract_value";
  defaultSortOrder?: "ascend" | "descend";
}

// Status tag colour (project status → antd Tag color). Ported verbatim.
const STATUS_TAG_COLOR: Record<string, string> = {
  active: "processing",
  draft: "default",
  completed: "success",
  on_hold: "warning",
};

// RAG band → antd Tag color. Ported verbatim.
const RAG_TAG_COLOR: Record<Exclude<RagBand, "Unknown">, string> = {
  Green: "success",
  Amber: "warning",
  Red: "error",
};

const PortfolioProjectsTableComponent: FC<
  WidgetComponentProps<PortfolioProjectsTableConfig>
> = ({
  config,
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
  onFullscreen,
  widgetType,
  dashboardName,
}) => {
  const ctx = useDashboardContext();

  // G16: branch FROZEN to main/merged (never reads ctx.branch / ctx.mode).
  const { data, isLoading, error, refetch } = usePortfolioEVM({
    controlDate: ctx.portfolioFilter?.controlDate ?? null,
    branch: "main",
    branchMode: "merged",
  });

  const { tableParams, handleTableChange } =
    useTableParams<PortfolioProjectMetrics>();

  const statusFilter = ctx.portfolioFilter?.status ?? null;
  const ragFilter = ctx.portfolioFilter?.rag ?? null;

  // Client-side status + RAG filter (ported verbatim from PortfolioPage ~L358-371).
  const filteredProjects = useMemo(() => {
    const rows = data?.projects ?? [];
    return rows.filter((row) => {
      if (statusFilter && statusFilter.length > 0) {
        if (!statusFilter.includes(row.status)) return false;
      }
      if (ragFilter && ragFilter.length > 0) {
        const band = ragBand(row.cpi ?? null, row.spi ?? null);
        if (band === "Unknown" || !ragFilter.includes(band)) return false;
      }
      return true;
    });
  }, [data?.projects, statusFilter, ragFilter]);

  // Resolved sort: URL-persisted sort wins over the config default. Ported from
  // PortfolioPage ~L380-392 but driven by `config.defaultSort*`, not roleLayout.
  const resolvedSort = useMemo(():
    | { field: string; order: SortOrder }
    | null => {
    if (tableParams.sortField && tableParams.sortOrder) {
      return {
        field: tableParams.sortField,
        order: tableParams.sortOrder as SortOrder,
      };
    }
    return config.defaultSortField && config.defaultSortOrder
      ? { field: config.defaultSortField, order: config.defaultSortOrder }
      : null;
  }, [tableParams.sortField, tableParams.sortOrder, config.defaultSortField, config.defaultSortOrder]);

  const columns = useMemo<ColumnType<PortfolioProjectMetrics>[]>(
    () => [
      {
        title: "Project",
        dataIndex: "name",
        key: "name",
        render: (_: unknown, record) => (
          <Link to={`/projects/${record.project_id}`}>{record.name}</Link>
        ),
        sorter: (a, b) => a.name.localeCompare(b.name),
        sortOrder:
          resolvedSort?.field === "name" ? resolvedSort.order : undefined,
        ellipsis: true,
      },
      {
        title: "Status",
        dataIndex: "status",
        key: "status",
        width: 130,
        render: (status: string) => (
          <Tag color={STATUS_TAG_COLOR[status] ?? "default"}>
            {status.replace(/_/g, " ")}
          </Tag>
        ),
        sorter: (a, b) => a.status.localeCompare(b.status),
        sortOrder:
          resolvedSort?.field === "status" ? resolvedSort.order : undefined,
      },
      {
        title: "CPI",
        dataIndex: "cpi",
        key: "cpi",
        width: 100,
        align: "right",
        render: (cpi: number | null | undefined) =>
          formatValue(cpi ?? null, "number"),
        sorter: (a, b) => (a.cpi ?? -Infinity) - (b.cpi ?? -Infinity),
        sortOrder:
          resolvedSort?.field === "cpi" ? resolvedSort.order : undefined,
      },
      {
        title: "SPI",
        dataIndex: "spi",
        key: "spi",
        width: 100,
        align: "right",
        render: (spi: number | null | undefined) =>
          formatValue(spi ?? null, "number"),
        sorter: (a, b) => (a.spi ?? -Infinity) - (b.spi ?? -Infinity),
        sortOrder:
          resolvedSort?.field === "spi" ? resolvedSort.order : undefined,
      },
      {
        title: "VAC",
        dataIndex: "vac",
        key: "vac",
        width: 140,
        align: "right",
        render: (vac: number | null | undefined) =>
          formatValue(vac ?? null, "currency", "EUR"),
        sorter: (a, b) => (a.vac ?? -Infinity) - (b.vac ?? -Infinity),
        sortOrder:
          resolvedSort?.field === "vac" ? resolvedSort.order : undefined,
      },
      {
        title: "Contract Value",
        dataIndex: "contract_value",
        key: "contract_value",
        width: 160,
        align: "right",
        render: (cv: number | null | undefined) =>
          formatValue(cv ?? null, "currency", "EUR"),
        sorter: (a, b) =>
          (a.contract_value ?? -Infinity) - (b.contract_value ?? -Infinity),
        sortOrder:
          resolvedSort?.field === "contract_value"
            ? resolvedSort.order
            : undefined,
      },
      {
        title: "RAG",
        key: "rag",
        width: 100,
        align: "center",
        render: (_: unknown, record) => {
          const band = ragBand(record.cpi ?? null, record.spi ?? null);
          if (band === "Unknown") return <Tag>Unknown</Tag>;
          return <Tag color={RAG_TAG_COLOR[band]}>{band}</Tag>;
        },
      },
    ],
    [resolvedSort],
  );

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Portfolio Projects"
      icon={<TableOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
      onFullscreen={onFullscreen}
      widgetType={widgetType}
      dashboardName={dashboardName}
    >
      <StandardTable<PortfolioProjectMetrics>
        rowKey="project_id"
        columns={columns}
        dataSource={filteredProjects}
        tableParams={tableParams}
        onChange={handleTableChange}
        size="middle"
      />
    </WidgetShell>
  );
};

registerWidget<PortfolioProjectsTableConfig>({
  typeId: widgetTypeId("portfolio-projects-table"),
  displayName: "Portfolio Projects",
  description:
    "Per-project portfolio breakdown table (Project, Status, CPI, SPI, VAC, Contract Value, RAG) with client-side status + RAG filtering.",
  category: "breakdown",
  icon: <TableOutlined />,
  sizeConstraints: {
    minW: 6,
    minH: 5,
    defaultW: 12,
    defaultH: 6,
    maxW: 12,
  },
  scope: "portfolio",
  requiredPermission: "portfolio-read",
  component: PortfolioProjectsTableComponent,
  defaultConfig: {},
});
