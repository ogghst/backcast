import { Form, Select, Space, Typography } from "antd";
import type { ConfigFormProps } from "./ConfigFormProps";

const { Text } = Typography;

export type EntityType = "PROJECT" | "WBE" | "COST_ELEMENT";

export interface EVMSummaryWidgetConfig {
  entityType?: EntityType;
}

const ENTITY_TYPE_OPTIONS = [
  { label: "Project", value: "PROJECT" as const },
  { label: "WBE (Work Breakdown Element)", value: "WBE" as const },
  { label: "Cost Element", value: "COST_ELEMENT" as const },
];

/**
 * Configuration form for EVM Summary widget.
 */
export function EVMSummaryConfigForm({
  config,
  onChange,
}: ConfigFormProps<EVMSummaryWidgetConfig>) {
  return (
    <Form layout="vertical">
      <Form.Item
        label="Entity Type"
        help="Choose the scope level for EVM metrics"
        required
      >
        <Space direction="vertical" size="small" style={{ width: "100%" }}>
          <Select
            value={config.entityType ?? "PROJECT"}
            onChange={(value) => onChange({ entityType: value })}
            options={ENTITY_TYPE_OPTIONS}
            style={{ width: "100%" }}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Project: Overall metrics • WBE: Work element metrics • Cost
            Element: Line item metrics
          </Text>
        </Space>
      </Form.Item>
    </Form>
  );
}
