import { Drawer, Table, Progress, Typography, Space } from "antd";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { formatCurrency } from "@/utils/formatters";
import { useWorkPackageAllocations } from "../api/useWorkPackages";
import type { QualityCostAllocationRead } from "../api/useWorkPackages";

const { Text } = Typography;

interface WorkPackageBreakdownDrawerProps {
  open: boolean;
  onClose: () => void;
  workPackageId: string | null;
  name?: string;
  totalCost?: number;
  currency?: string;
}

export const WorkPackageBreakdownDrawer = ({
  open,
  onClose,
  workPackageId,
  name,
  totalCost = 0,
  currency = "EUR",
}: WorkPackageBreakdownDrawerProps) => {
  const { spacing, colors, typography } = useThemeTokens();

  const { data: allocations, isLoading } = useWorkPackageAllocations(
    workPackageId || "",
  );

  const items = allocations || [];
  const allocated = items.reduce(
    (sum, a) => sum + Number(a.amount || 0),
    0,
  );
  const unallocated = Math.max(0, totalCost - allocated);
  const allocatedPct =
    totalCost > 0 ? Math.round((allocated / totalCost) * 100) : 0;

  const columns = [
    {
      title: "WBE Code",
      dataIndex: "wbe_code",
      key: "wbe_code",
      render: (code: string | undefined) => code || "-",
    },
    {
      title: "Cost Element",
      dataIndex: "cost_element_name",
      key: "cost_element_name",
      render: (cename: string | undefined) => cename || "-",
    },
    {
      title: "Amount",
      dataIndex: "amount",
      key: "amount",
      align: "right" as const,
      render: (amount: number) => (
        <span style={{ fontWeight: typography.weights.medium }}>
          {formatCurrency(amount, currency)}
        </span>
      ),
    },
  ];

  return (
    <Drawer
      title={`Cost Allocations${name ? ` - ${name}` : ""}`}
      placement="right"
      onClose={onClose}
      open={open}
      width={400}
    >
      <Space
        direction="vertical"
        style={{ width: "100%" }}
        size={spacing.md}
      >
        {/* Summary */}
        <div
          style={{
            padding: spacing.md,
            background: colors.bgLayout,
            borderRadius: spacing.sm,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: spacing.sm,
            }}
          >
            <Text type="secondary">Planned Cost</Text>
            <Text strong>
              {formatCurrency(totalCost, currency)}
            </Text>
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: spacing.sm,
            }}
          >
            <Text type="secondary">Allocated</Text>
            <Text style={{ color: colors.success }}>
              {formatCurrency(allocated, currency)}
            </Text>
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: spacing.sm,
            }}
          >
            <Text type="secondary">Unallocated</Text>
            <Text
              style={{
                color: unallocated > 0 ? colors.warning : colors.success,
              }}
            >
              {formatCurrency(unallocated, currency)}
            </Text>
          </div>
          <Progress
            percent={allocatedPct}
            size="small"
            status={unallocated > 0 ? "active" : "success"}
          />
        </div>

        {/* Allocations Table */}
        <Table<QualityCostAllocationRead>
          columns={columns}
          dataSource={items}
          rowKey="cost_registration_id"
          loading={isLoading}
          pagination={false}
          size="small"
        />
      </Space>
    </Drawer>
  );
};
