/**
 * Agents History Page
 *
 * Lists agent executions (including background runs) with status filtering,
 * a Stop action for active runs, and a deep-link "Open chat" action. Ownership
 * is enforced by the backend; this page only lists what the user owns.
 */

import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { App, Button, Popconfirm, Segmented, Space, Table, Tag, Tooltip, Typography, theme } from "antd";
import type { ColumnType } from "antd/es/table";
import {
  StopOutlined,
  MessageOutlined,
} from "@ant-design/icons";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import {
  useAgentExecutions,
  useStopExecution,
  type AgentExecutionHistoryItem,
} from "@/features/ai/chat/api/useAgentExecutions";

const { Title } = Typography;

type StatusFilter = "all" | "running" | "completed" | "error" | "stopped";

const STATUS_COLOR: Record<string, string> = {
  running: "processing",
  completed: "success",
  error: "error",
  stopped: "warning",
  awaiting_approval: "gold",
};

function formatRelative(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  // Absolute datetime; keeps it deterministic and locale-aware.
  return d.toLocaleString();
}

function formatDuration(startedAt: string, completedAt: string | null): string {
  if (!completedAt) return "—";
  const start = new Date(startedAt).getTime();
  const end = new Date(completedAt).getTime();
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return "—";
  const ms = end - start;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remSeconds = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const remMinutes = minutes % 60;
  return `${hours}h ${remMinutes}m`;
}

function deriveContextLabel(item: AgentExecutionHistoryItem): string {
  if (item.context?.project_id && item.context?.name) {
    return `Project: ${item.context.name}`;
  }
  if (item.context?.branch_id) return "Branch";
  if (item.context?.project_id) return "Project";
  return "Global";
}

function deriveName(item: AgentExecutionHistoryItem): string {
  return (
    item.name ??
    item.assistant_name ??
    item.id.slice(0, 8)
  );
}

export const AgentsHistory = () => {
  const { token } = theme.useToken();
  const { spacing } = useThemeTokens();
  const navigate = useNavigate();
  const { message } = App.useApp();

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const executionsQuery = useAgentExecutions({
    status: statusFilter,
    limit: 50,
    offset: 0,
  });
  const stopExecution = useStopExecution({
    onSuccess: () => message.success("Agent stop requested"),
  });

  const handleOpenChat = (item: AgentExecutionHistoryItem) => {
    navigate("/chat", {
      state: { sessionId: item.session_id, executionId: item.id },
    });
  };

  const handleStop = (item: AgentExecutionHistoryItem) => {
    stopExecution.mutate(item.id);
  };

  const columns = useMemo<ColumnType<AgentExecutionHistoryItem>[]>(
    () => [
      {
        title: "Name",
        dataIndex: "name",
        key: "name",
        render: (_, record) => deriveName(record),
        ellipsis: true,
      },
      {
        title: "Status",
        dataIndex: "status",
        key: "status",
        width: 150,
        render: (status: string) => (
          <Tag color={STATUS_COLOR[status] ?? "default"}>
            {status.replace(/_/g, " ")}
          </Tag>
        ),
      },
      {
        title: "Context",
        key: "context",
        width: 160,
        render: (_, record) => deriveContextLabel(record),
      },
      {
        title: "Started",
        dataIndex: "started_at",
        key: "started_at",
        width: 200,
        render: (iso: string) => formatRelative(iso),
      },
      {
        title: "Duration",
        key: "duration",
        width: 110,
        render: (_, record) =>
          formatDuration(record.started_at, record.completed_at),
      },
      {
        title: "Assistant",
        dataIndex: "assistant_name",
        key: "assistant_name",
        width: 150,
        render: (name: string | null) => name ?? "—",
        ellipsis: true,
      },
      {
        title: "Actions",
        key: "actions",
        width: 160,
        render: (_, record) => {
          const isActive =
            record.status === "running" ||
            record.status === "awaiting_approval";
          return (
            <Space size={spacing.xs}>
              <Tooltip title="Open chat">
                <Button
                  type="text"
                  size="small"
                  icon={<MessageOutlined />}
                  onClick={() => handleOpenChat(record)}
                  aria-label="Open chat"
                />
              </Tooltip>
              <Popconfirm
                title="Stop this agent run?"
                description="The agent will be terminated."
                okText="Stop"
                okButtonProps={{ danger: true }}
                cancelText="Cancel"
                onConfirm={() => handleStop(record)}
                disabled={!isActive}
              >
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<StopOutlined />}
                  disabled={!isActive}
                  loading={stopExecution.isPending}
                  aria-label="Stop agent"
                />
              </Popconfirm>
            </Space>
          );
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [spacing.xs, stopExecution.isPending],
  );

  return (
    <PageWrapper>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: spacing.md,
          marginBottom: spacing.md,
          flexWrap: "wrap",
        }}
      >
        <Title level={2} style={{ margin: 0 }}>
          Agents History
        </Title>
        <Segmented<StatusFilter>
          value={statusFilter}
          onChange={(val) => setStatusFilter(val)}
          options={[
            { label: "All", value: "all" },
            { label: "Running", value: "running" },
            { label: "Completed", value: "completed" },
            { label: "Error", value: "error" },
            { label: "Stopped", value: "stopped" },
          ]}
        />
      </div>

      <Table<AgentExecutionHistoryItem>
        rowKey="id"
        columns={columns}
        dataSource={executionsQuery.data?.items ?? []}
        loading={executionsQuery.isLoading}
        pagination={false}
        size="middle"
        locale={{ emptyText: "No agent executions" }}
        style={{
          backgroundColor: token.colorBgContainer,
          borderRadius: token.borderRadiusLG,
        }}
      />
    </PageWrapper>
  );
};

export default AgentsHistory;
