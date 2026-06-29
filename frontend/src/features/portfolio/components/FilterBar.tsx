/**
 * Portfolio filter bar.
 *
 * Composes the date range picker + Status multi-select + RAG multi-select and
 * binds them to the portfolio filter store. v1 = Date + Status + RAG only
 * (locked decision — no BU/PM/customer selectors).
 *
 * Uses design tokens for all spacing/colour (no hardcoded values). The RAG
 * options carry coloured Tag labels so the selection is visually scannable.
 */

import { Button, Select, Space, Tag, theme } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { usePortfolioFilterStore } from "@/stores/usePortfolioFilterStore";
import { PortfolioDateRangePicker } from "./PortfolioDateRangePicker";
import type { RagBand } from "@/features/widgets/definitions/shared/portfolioMetrics";

const STATUS_OPTIONS = [
  { label: "Active", value: "active" },
  { label: "Draft", value: "draft" },
  { label: "Completed", value: "completed" },
  { label: "On Hold", value: "on_hold" },
];

/** RAG band → antd Tag color (semantic token names where possible). */
const RAG_TAG_COLOR: Record<Exclude<RagBand, "Unknown">, string> = {
  Green: "success",
  Amber: "warning",
  Red: "error",
};

const RAG_OPTIONS: { label: React.ReactNode; value: string }[] = (
  ["Green", "Amber", "Red"] as const
).map((band) => ({
  value: band,
  label: <Tag color={RAG_TAG_COLOR[band]}>{band}</Tag>,
}));

export function FilterBar(): React.JSX.Element {
  const { token } = theme.useToken();
  const { spacing } = useThemeTokens();

  const controlDate = usePortfolioFilterStore((s) => s.controlDate);
  const status = usePortfolioFilterStore((s) => s.status);
  const rag = usePortfolioFilterStore((s) => s.rag);
  const setControlDate = usePortfolioFilterStore((s) => s.setControlDate);
  const setStatus = usePortfolioFilterStore((s) => s.setStatus);
  const setRag = usePortfolioFilterStore((s) => s.setRag);
  const resetFilters = usePortfolioFilterStore((s) => s.resetFilters);

  return (
    <Space
      size={spacing.md}
      wrap
      style={{
        padding: `${spacing.sm}px ${spacing.md}px`,
        background: token.colorBgContainer,
        borderRadius: token.borderRadiusLG,
        marginBottom: spacing.md,
      }}
    >
      <PortfolioDateRangePicker
        controlDate={controlDate}
        onChange={setControlDate}
      />

      <Select
        mode="multiple"
        allowClear
        placeholder="Status"
        value={status ?? []}
        onChange={(vals: string[]) => setStatus(vals.length > 0 ? vals : null)}
        options={STATUS_OPTIONS}
        style={{ minWidth: 180 }}
        aria-label="Filter by status"
        maxTagCount="responsive"
      />

      <Select
        mode="multiple"
        allowClear
        placeholder="RAG"
        value={rag ?? []}
        onChange={(vals: string[]) => setRag(vals.length > 0 ? vals : null)}
        options={RAG_OPTIONS}
        style={{ minWidth: 160 }}
        aria-label="Filter by RAG band"
        maxTagCount="responsive"
      />

      <Button
        icon={<ReloadOutlined />}
        onClick={resetFilters}
        aria-label="Reset filters"
      >
        Reset
      </Button>
    </Space>
  );
}
