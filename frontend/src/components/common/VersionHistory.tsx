import { Drawer, List, Button, Tag, Typography, Space } from "antd";
import { HistoryOutlined, UndoOutlined } from "@ant-design/icons";
import dayjs from "dayjs";

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
      size={400}
    >
      <List
        loading={isLoading}
        itemLayout="vertical"
        dataSource={versions}
        renderItem={(item) => (
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
                <Space>
                  <Tag color="blue">v{item.id}</Tag>
                  <Typography.Text type="secondary">
                    {dayjs(item.valid_from).format("YYYY-MM-DD HH:mm")}
                  </Typography.Text>
                </Space>
              }
              description={
                <div>
                  <div>Changed by: {item.changed_by || "Unknown"}</div>
                  {/* Simplistic diff view for now */}
                  {item.changes && (
                    <Typography.Text code>
                      {Object.keys(item.changes).join(", ")} changed
                    </Typography.Text>
                  )}
                </div>
              }
            />
          </List.Item>
        )}
      />
    </Drawer>
  );
};
