import { Form, Select, Space, Typography } from "antd";
import type { ConfigFormProps } from "./ConfigFormProps";
import { EntityType } from "@/features/evm/types";

const { Text } = Typography;

export interface EVMSummaryConfig {
  entityType?: EntityType;
}

const ENTITY_TYPE_OPTIONS = [
  { label: "Project", value: EntityType.PROJECT },
  { label: "WBS Element", value: EntityType.WBS_ELEMENT },
  { label: "Cost Element", value: EntityType.COST_ELEMENT },
  { label: "Work Package", value: EntityType.WORK_PACKAGE },
];

/**
 * Configuration form for EVM Summary widget.
 */
export function EVMSummaryConfigForm({
  config,
  onChange,
}: ConfigFormProps<EVMSummaryConfig>) {
  return (
    <Form layout="vertical">
      <Form.Item
        label="Entity Type"
        help="Choose the scope level for EVM metrics"
        required
      >
        <Space direction="vertical" size="small" style={{ width: "100%" }}>
          <Select
            value={config.entityType ?? EntityType.PROJECT}
            onChange={(value) => onChange({ entityType: value })}
            options={ENTITY_TYPE_OPTIONS}
            style={{ width: "100%" }}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Project: Overall metrics • WBS Element: Work element metrics •
            Work Package: PMI budget holder • Cost Element: Line item metrics
          </Text>
        </Space>
      </Form.Item>
    </Form>
  );
}
