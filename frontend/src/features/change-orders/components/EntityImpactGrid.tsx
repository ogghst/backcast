import { Card, Table, Tag, Typography, Empty } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { EntityChanges, EntityChange, EntityChangeType } from "@/api/generated";

const { Title } = Typography;

interface EntityImpactGridProps {
  entityChanges: EntityChanges | undefined;
  loading?: boolean;
}

/**
 * Formats a decimal string to EUR currency.
 */
const formatCurrency = (value: string | null | undefined): string => {
  if (!value) return "€0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "EUR",
  }).format(Number(value));
};

/**
 * Gets the color for a change type tag.
 */
const getChangeTypeColor = (type: EntityChangeType): string => {
  switch (type) {
    case "added":
      return "green";
    case "modified":
      return "blue";
    case "removed":
      return "red";
    default:
      return "default";
  }
};

/**
 * EntityImpactGrid Component
 *
 * Displays a table of entity changes (WBEs and Cost Elements) showing:
 * - Entity name and type
 * - Change type (Added/Modified/Removed)
 * - Budget delta
 * - Revenue delta
 * - Cost delta
 */
export const EntityImpactGrid = ({
  entityChanges,
  loading,
}: EntityImpactGridProps) => {
  // Combine WBEs and Cost Elements into a single list
  const allChanges: Array<EntityChange & { entityType: string }> = [
    ...(entityChanges?.wbes?.map((wbe) => ({ ...wbe, entityType: "WBE" })) || []),
    ...(entityChanges?.cost_elements?.map((ce) => ({ ...ce, entityType: "Cost Element" })) || []),
  ];

  if (allChanges.length === 0) {
    return (
      <Card loading={loading ?? false}>
        <Title level={4}>Entity Changes</Title>
        <Empty description="No entity changes detected" />
      </Card>
    );
  }

  const columns: ColumnsType<EntityChange & { entityType: string }> = [
    {
      title: "Entity",
      dataIndex: "name",
      key: "name",
      width: "30%",
      render: (name: string, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{name}</div>
          <div style={{ fontSize: 12, color: "#8c8c8c" }}>ID: {record.id}</div>
        </div>
      ),
    },
    {
      title: "Type",
      dataIndex: "entityType",
      key: "entityType",
      width: "15%",
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: "Change",
      dataIndex: "change_type",
      key: "change_type",
      width: "15%",
      render: (type: EntityChangeType) => (
        <Tag color={getChangeTypeColor(type)}>{type.toUpperCase()}</Tag>
      ),
    },
    {
      title: "Budget Delta",
      dataIndex: "budget_delta",
      key: "budget_delta",
      width: "15%",
      align: "right" as const,
      render: (value: string | null | undefined) => {
        if (value === null || value === undefined) return <span style={{ color: "#8c8c8c" }}>-</span>;
        const num = Number(value);
        const color = num > 0 ? "#cf1322" : num < 0 ? "#3f8600" : undefined;
        return <span style={{ color, fontWeight: 500 }}>{formatCurrency(value)}</span>;
      },
    },
    {
      title: "Revenue Delta",
      dataIndex: "revenue_delta",
      key: "revenue_delta",
      width: "15%",
      align: "right" as const,
      render: (value: string | null | undefined) => {
        if (value === null || value === undefined) return <span style={{ color: "#8c8c8c" }}>-</span>;
        const num = Number(value);
        const color = num > 0 ? "#cf1322" : num < 0 ? "#3f8600" : undefined;
        return <span style={{ color, fontWeight: 500 }}>{formatCurrency(value)}</span>;
      },
    },
    {
      title: "Cost Delta",
      dataIndex: "cost_delta",
      key: "cost_delta",
      width: "15%",
      align: "right" as const,
      render: (value: string | null | undefined) => {
        if (value === null || value === undefined) return <span style={{ color: "#8c8c8c" }}>-</span>;
        const num = Number(value);
        const color = num > 0 ? "#cf1322" : num < 0 ? "#3f8600" : undefined;
        return <span style={{ color, fontWeight: 500 }}>{formatCurrency(value)}</span>;
      },
    },
  ];

  return (
    <Card loading={loading ?? false}>
      <Title level={4}>Entity Changes</Title>
      <Table
        dataSource={allChanges}
        columns={columns}
        rowKey={(record) => `${record.entityType}-${record.id}`}
        pagination={false}
        size="small"
      />
    </Card>
  );
};
