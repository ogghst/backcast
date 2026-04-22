import { Table, Button, Tag, theme, Grid, Typography, Empty, Spin } from "antd";
import type { ColumnType } from "antd/es/table";
import { WBERead } from "@/api/generated";
import { RightOutlined } from "@ant-design/icons";
import { EntityCard } from "@/components/common/EntityCard";
import type { ViewMode } from "@/hooks/useViewMode";
import { formatCurrency } from "@/utils/formatters";
import { useMemo } from "react";

const { useBreakpoint } = Grid;
const { Text } = Typography;

export interface WBETablePagination {
  current: number;
  pageSize: number;
  total: number;
  onChange: (page: number, pageSize: number) => void;
}

interface WBETableProps {
  wbes: WBERead[];
  loading?: boolean;
  onRowClick?: (wbe: WBERead) => void;
  variant?: ViewMode;
  pagination?: WBETablePagination;
}

export const WBETable = ({
  wbes,
  loading,
  onRowClick,
  variant = "auto",
  pagination,
}: WBETableProps) => {
  const { token } = theme.useToken();
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const isTablet = !!screens.md && !screens.lg;

  const useCard = variant === "card" || (variant === "auto" && isMobile);

  const columns: ColumnType<WBERead>[] = useMemo(() => {
    const cols: ColumnType<WBERead>[] = [
      {
        title: "Code",
        dataIndex: "code",
        key: "code",
        width: 100,
        sorter: (a, b) =>
          a.code.localeCompare(b.code, undefined, { numeric: true }),
      },
      {
        title: "Name",
        dataIndex: "name",
        key: "name",
        sorter: (a, b) => a.name.localeCompare(b.name),
      },
    ];

    if (!isMobile) {
      cols.push({
        title: "Budget",
        dataIndex: "budget_allocation",
        key: "budget_allocation",
        render: (val) => (val ? formatCurrency(val) : "-"),
        width: 150,
        align: "right",
        sorter: (a, b) =>
          Number(a.budget_allocation || 0) - Number(b.budget_allocation || 0),
      });
    }

    if (!isMobile && !isTablet) {
      cols.push({
        title: "Branch",
        dataIndex: "branch",
        key: "branch",
        width: 120,
        render: (val) => (val ? <Tag>{val}</Tag> : "-"),
        sorter: (a, b) => a.branch.localeCompare(b.branch),
      });
    }

    cols.push({
      title: "",
      key: "actions",
      width: 50,
      align: "center",
      render: (_, record) => (
        <Button
          type="text"
          size="small"
          icon={<RightOutlined />}
          onClick={(e) => {
            e.stopPropagation();
            onRowClick?.(record);
          }}
        />
      ),
    });

    return cols;
  }, [isMobile, isTablet, onRowClick]);

  if (useCard) {
    if (loading) {
      return (
        <div style={{ display: "flex", justifyContent: "center", padding: token.paddingXL }}>
          <Spin />
        </div>
      );
    }
    if (wbes.length === 0) {
      return <Empty description="No work breakdown elements" />;
    }
    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: token.marginMD,
        }}
      >
        {wbes.map((wbe) => (
          <EntityCard
            key={wbe.wbe_id}
            title={wbe.name}
            subtitle={wbe.code}
            onClick={() => onRowClick?.(wbe)}
            metrics={
              wbe.budget_allocation
                ? (
                  <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                    Budget: {formatCurrency(wbe.budget_allocation)}
                  </Text>
                )
                : undefined
            }
            meta={
              <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                Branch: {wbe.branch || "main"}
              </Text>
            }
          />
        ))}
      </div>
    );
  }

  return (
    <Table
      dataSource={wbes}
      columns={columns}
      rowKey="wbe_id"
      loading={loading}
      scroll={{ x: isTablet ? 600 : undefined }}
      onRow={(record) => ({
        onClick: () => onRowClick?.(record),
        style: { cursor: "pointer" },
      })}
      pagination={
        pagination
          ? {
              current: pagination.current,
              pageSize: pagination.pageSize,
              total: pagination.total,
              onChange: pagination.onChange,
              showSizeChanger: true,
              pageSizeOptions: ["10", "20", "50", "100"],
              showTotal: (total) => `Total ${total} items`,
              position: ["bottomRight"],
            }
          : {
              defaultPageSize: 10,
              showSizeChanger: true,
              pageSizeOptions: ["10", "20", "50", "100"],
              showTotal: (total) => `Total ${total} items`,
              position: ["bottomRight"],
            }
      }
    />
  );
};
