import { Form, InputNumber, Space, Typography } from "antd";
import type { ConfigFormProps } from "./ConfigFormProps";

const { Text } = Typography;

export interface CostRegistrationsWidgetConfig {
  pageSize?: number;
}

/**
 * Configuration form for Cost Registrations widget.
 */
export function CostRegistrationsConfigForm({
  config,
  onChange,
}: ConfigFormProps<CostRegistrationsWidgetConfig>) {
  return (
    <Form layout="vertical">
      <Form.Item
        label="Page Size"
        help="Number of registrations to display per page (5-100)"
      >
        <Space direction="vertical" size="small" style={{ width: "100%" }}>
          <InputNumber
            min={5}
            max={100}
            value={config.pageSize ?? 20}
            onChange={(value) => onChange({ pageSize: value ?? 20 })}
            style={{ width: "100%" }}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Larger page sizes may impact performance
          </Text>
        </Space>
      </Form.Item>
    </Form>
  );
}
