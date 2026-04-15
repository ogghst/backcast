import { Drawer, List, Button, Typography, Space, Divider } from "antd";
import { HistoryOutlined, UndoOutlined, ClockCircleOutlined } from "@ant-design/icons";
import { formatTemporalDate } from "@/utils/temporal";

const { Text } = Typography;

interface Version {
  id: string;
  valid_from: string;
  transaction_time: string;
  changed_by?: string;
  changes?: Record<string, unknown>;
}

interface VersionHistoryDrawerProps {
  open: boolean;
  onClose: () => void;
  versions: Version[];
  entityName: string;
  onRestore?: (versionId: string) => void;
  isLoading?: boolean;
}

export const VersionHistoryDrawer = ({
  open,
  onClose,
  versions,
  entityName,
  onRestore,
  isLoading,
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
          const changes = item.changes as Record<string, string> | undefined;
          const validFrom = changes?.valid_from
            ? formatTemporalDate(changes.valid_from)
            : "Unknown";
          const validTo = changes?.valid_to;
          const validToDisplay = validTo === "Present"
            ? "Present"
            : (validTo ? formatTemporalDate(validTo) : "Unknown");
          const transactionTime = changes?.transaction_time
            ? formatTemporalDate(changes.transaction_time)
            : "Unknown";

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
                        <Text style={{ fontSize: "12px" }}>
                          {validFrom} → {validToDisplay}
                        </Text>
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
