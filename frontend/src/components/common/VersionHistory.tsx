import { Drawer, List, Button, Typography, Space, Divider } from "antd";
import { HistoryOutlined, UndoOutlined, ClockCircleOutlined } from "@ant-design/icons";
import {
  formatDate,
  formatTemporalRange,
  type DateFormatStyle,
} from "@/utils/formatters";

const { Text } = Typography;

interface Version {
  id: string;
  valid_from: string;
  transaction_time: string;
  changed_by?: string;
  changes?: Record<string, unknown>;
  valid_to?: string | null;
  // New backend-formatted temporal fields
  valid_time_formatted?: {
    lower: string | null;
    upper: string | null;
    lower_formatted: string;
    upper_formatted: string;
    is_currently_valid: boolean;
  };
  transaction_time_formatted?: {
    lower: string | null;
    upper: string | null;
    lower_formatted: string;
    upper_formatted: string;
    is_currently_valid: boolean;
  };
}

interface VersionHistoryDrawerProps {
  open: boolean;
  onClose: () => void;
  versions: Version[];
  entityName: string;
  onRestore?: (versionId: string) => void;
  isLoading?: boolean;
  /** Date format style for locale-aware formatting (default: "medium") */
  dateFormatStyle?: DateFormatStyle;
}

export const VersionHistoryDrawer = ({
  open,
  onClose,
  versions,
  entityName,
  onRestore,
  isLoading,
  dateFormatStyle = "medium",
}: VersionHistoryDrawerProps) => {
  return (
    <Drawer
      title={
        <Space>
          <HistoryOutlined />
          {entityName} History
        </Space>
      }
      placement="right"
      onClose={onClose}
      open={open}
      size={450}
    >
      <List
        loading={isLoading}
        itemLayout="vertical"
        dataSource={versions}
        renderItem={(item, index) => {
          // Use backend-formatted temporal data (new API format)
          // Format using browser locale for better UX
          const validFrom = item.valid_time_formatted
            ? formatDate(item.valid_from, {
                style: dateFormatStyle,
                fallback: item.valid_time_formatted.lower_formatted || "Unknown",
              })
            : formatDate(item.valid_from, { style: dateFormatStyle });

          const transactionTime = item.transaction_time_formatted
            ? formatDate(item.transaction_time, {
                style: dateFormatStyle,
                fallback: item.transaction_time_formatted.lower_formatted || "Unknown",
              })
            : formatDate(item.transaction_time, { style: dateFormatStyle });

          // Format valid time range using locale
          const validTimeRange = item.valid_time_formatted
            ? formatTemporalRange(item.valid_time_formatted, { style: dateFormatStyle })
            : `${validFrom} – Present`;

          return (
            <List.Item
              actions={[
                onRestore && (
                  <Button
                    size="small"
                    icon={<UndoOutlined />}
                    onClick={() => onRestore(item.id)}
                  >
                    Restore
                  </Button>
                ),
              ]}
            >
              <List.Item.Meta
                title={
                  <Text type="secondary">Valid from {validFrom}</Text>
                }
                description={
                  <div style={{ marginTop: 8 }}>
                    <Space direction="vertical" size="small" style={{ width: "100%" }}>
                      {/* Valid Time Range */}
                      <div>
                        <Text type="secondary" strong>
                          Valid Time:
                        </Text>
                        <br />
                        <Text style={{ fontSize: "12px" }}>{validTimeRange}</Text>
                      </div>

                      {/* Transaction Time */}
                      <div>
                        <ClockCircleOutlined style={{ marginRight: 4 }} />
                        <Text type="secondary" strong>
                          Recorded:
                        </Text>{" "}
                        <Text style={{ fontSize: "12px" }}>{transactionTime}</Text>
                      </div>

                      {/* Changed By */}
                      <div>
                        <Text type="secondary" strong>
                          Changed by:
                        </Text>{" "}
                        <Text>{item.changed_by || "Unknown"}</Text>
                      </div>

                      {index !== versions.length - 1 && <Divider style={{ margin: "4px 0" }} />}
                    </Space>
                  </div>
                }
              />
            </List.Item>
          );
        }}
      />
    </Drawer>
  );
};
