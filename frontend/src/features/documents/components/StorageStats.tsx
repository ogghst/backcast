import React from "react";
import { Progress, Space, Typography, theme, Tooltip } from "antd";
import { DatabaseOutlined } from "@ant-design/icons";
import { formatFileSize } from "@/features/ai/chat/api/attachmentUpload";
import { useStorageStats } from "../api/documentApi";

const { Text } = Typography;

interface StorageStatsProps {
  projectId: string;
}

/** 1 GB ceiling for the progress bar display */
const STORAGE_CEILING_BYTES = 1 * 1024 * 1024 * 1024;

export const StorageStats: React.FC<StorageStatsProps> = ({ projectId }) => {
  const { token } = theme.useToken();
  const { data: stats } = useStorageStats(projectId);

  if (!stats) return null;

  const percent = Math.min(
    Math.round((stats.total_bytes / STORAGE_CEILING_BYTES) * 100),
    100,
  );

  return (
    <Tooltip
      title={
        <Space direction="vertical" size={0}>
          <Text style={{ color: "inherit" }}>
            {formatFileSize(stats.total_bytes)} used
          </Text>
          <Text style={{ color: "inherit", fontSize: token.fontSizeSM }}>
            {stats.file_count} files, {stats.version_count} versions
          </Text>
        </Space>
      }
    >
      <div style={{ display: "flex", alignItems: "center", gap: token.marginXS, minWidth: 140 }}>
        <DatabaseOutlined style={{ color: token.colorTextSecondary, fontSize: 14 }} />
        <Progress
          percent={percent}
          size="small"
          showInfo={false}
          strokeColor={percent > 80 ? token.colorError : token.colorPrimary}
          style={{ flex: 1, marginBottom: 0 }}
        />
        <Text type="secondary" style={{ fontSize: token.fontSizeSM, whiteSpace: "nowrap" }}>
          {formatFileSize(stats.total_bytes)}
        </Text>
      </div>
    </Tooltip>
  );
};
