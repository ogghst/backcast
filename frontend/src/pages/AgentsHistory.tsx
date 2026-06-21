/**
 * Agents History Page
 *
 * Lists agent executions (including background runs) with status filtering,
 * a Stop action for active runs, and a deep-link "Open chat" action. Ownership
 * is enforced by the backend; this page only lists what the user owns.
 */

import { useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { App, Button, DatePicker, Empty, Grid, Popconfirm, Segmented, Space, Spin, Table, Tag, Tooltip, Typography, theme } from "antd";
import type { ColumnType } from "antd/es/table";
import dayjs, { type Dayjs } from "dayjs";
import {
  ArrowLeftOutlined,
  StopOutlined,
  MessageOutlined,
} from "@ant-design/icons";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { EntityCard } from "@/components/common/EntityCard";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import {
  useAgentExecutions,
  useStopExecution,
  type AgentExecutionHistoryItem,
} from "@/features/ai/chat/api/useAgentExecutions";
import { useAgentSchedule } from "@/features/ai/schedules/api/useAgentSchedules";

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

// Compact label/value row for the mobile card meta zone.
const DetailRow = ({ label, value }: { label: string; value: string }) => (
  <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
    <span>{label}</span>
    <span style={{ color: "inherit", textAlign: "right" }}>{value}</span>
  </div>
);

export const AgentsHistory = () => {
  const { token } = theme.useToken();
  const { spacing } = useThemeTokens();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { message } = App.useApp();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md; // md breakpoint = 768px

  // URL-driven filters: `schedule` (= schedule_id), `from` / `to` (ISO datetimes).
  const scheduleId = searchParams.get("schedule") ?? undefined;
  const fromIso = searchParams.get("from") ?? undefined;
  const toIso = searchParams.get("to") ?? undefined;
  const isScoped = !!scheduleId;

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const executionsQuery = useAgentExecutions({
    status: statusFilter,
    limit: 50,
    offset: 0,
    scheduleId,
    startedFrom: fromIso,
    startedTo: toIso,
  });

  // When scoped, fetch the schedule's name for the title. Falls back to a
  // generic label while loading / on error.
  const scheduleQuery = useAgentSchedule(scheduleId ?? "");
  const scheduleName = isScoped
    ? scheduleQuery.data?.name ?? "Schedule runs"
    : null;

  const stopExecution = useStopExecution({
    onSuccess: () => message.success("Agent stop requested"),
  });

  // RangePicker value derives from the `from`/`to` search params.
  const rangeValue: [Dayjs | null, Dayjs | null] | null = useMemo(() => {
    if (!fromIso && !toIso) return null;
    const start = fromIso ? dayjs(fromIso) : null;
    const end = toIso ? dayjs(toIso) : null;
    return [start, end];
  }, [fromIso, toIso]);

  const handleRangeChange = (
    range: [Dayjs | null, Dayjs | null] | null,
  ) => {
    const next = new URLSearchParams(searchParams);
    if (range && range[0] && range[1]) {
      next.set("from", range[0].startOf("day").toISOString());
      next.set("to", range[1].endOf("day").toISOString());
    } else {
      next.delete("from");
      next.delete("to");
    }
    setSearchParams(next, { replace: true });
  };

  // When scoped, returning from chat re-enters the filtered view (preserve the
  // full path + current filters). Unscoped keeps the original behaviour.
  const returnTo = isScoped
    ? `${location.pathname}${location.search}`
    : "/agents-history";

  const handleOpenChat = (item: AgentExecutionHistoryItem) => {
    navigate("/chat?ctx=general", {
      state: {
        sessionId: item.session_id,
        executionId: item.id,
        returnTo,
      },
    });
  };

  const handleStop = (item: AgentExecutionHistoryItem) => {
    stopExecution.mutate(item.id);
  };

  // Shared action buttons (Open chat + Stop), identical on desktop and mobile.
  const renderActions = (record: AgentExecutionHistoryItem) => {
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
  };

  const columns = useMemo<ColumnType<AgentExecutionHistoryItem>[]>(
    () => [
      {
        title: "Name",
        dataIndex: "name",
        key: "name",
        render: (_, record) => (
          <Space size={spacing.xs}>
            <span>{deriveName(record)}</span>
            {record.schedule_id ? <Tag color="blue">scheduled</Tag> : null}
          </Space>
        ),
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
        render: (_, record) => renderActions(record),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [spacing.xs, stopExecution.isPending],
  );

  const renderMobileCard = (record: AgentExecutionHistoryItem) => (
    <EntityCard
      title={deriveName(record)}
      badge={
        <Space size={spacing.xs}>
          <Tag color={STATUS_COLOR[record.status] ?? "default"}>
            {record.status.replace(/_/g, " ")}
          </Tag>
          {record.schedule_id ? <Tag color="blue">scheduled</Tag> : null}
        </Space>
      }
      meta={
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: spacing.xs,
            fontSize: token.fontSizeSM,
            color: token.colorTextSecondary,
          }}
        >
          <DetailRow label="Context" value={deriveContextLabel(record)} />
          <DetailRow
            label="Started"
            value={formatRelative(record.started_at)}
          />
          <DetailRow
            label="Duration"
            value={formatDuration(record.started_at, record.completed_at)}
          />
          <DetailRow
            label="Assistant"
            value={record.assistant_name ?? "—"}
          />
        </div>
      }
      actions={renderActions(record)}
    />
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
        <Space size={spacing.sm} align="center">
          {isScoped ? (
            <Tooltip title="Back to schedules">
              <Button
                icon={<ArrowLeftOutlined />}
                onClick={() => navigate("/admin/agent-schedules")}
                aria-label="Back to schedules"
              />
            </Tooltip>
          ) : null}
          <Title level={2} style={{ margin: 0 }}>
            {isScoped ? `Runs — ${scheduleName}` : "Agents History"}
          </Title>
        </Space>
        <Space
          size={spacing.sm}
          // On narrow phones the filters would clip; let them take the full row
          // below the title. Desktop layout is unchanged.
          style={isMobile ? { width: "100%" } : undefined}
          wrap
        >
          <DatePicker.RangePicker
            value={rangeValue}
            onChange={(range) =>
              handleRangeChange(
                range as [Dayjs | null, Dayjs | null] | null,
              )
            }
            style={isMobile ? { width: "100%" } : undefined}
            aria-label="Filter by date range"
          />
          <Segmented<StatusFilter>
            value={statusFilter}
            onChange={(val) => setStatusFilter(val)}
            style={isMobile ? { width: "100%" } : undefined}
            options={[
              { label: "All", value: "all" },
              { label: "Running", value: "running" },
              { label: "Completed", value: "completed" },
              { label: "Error", value: "error" },
              { label: "Stopped", value: "stopped" },
            ]}
          />
        </Space>
      </div>

      {isMobile ? (
        executionsQuery.isLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: spacing.xl }}>
            <Spin />
          </div>
        ) : (executionsQuery.data?.items ?? []).length === 0 ? (
          <Empty description="No agent executions" />
        ) : (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: spacing.sm,
            }}
          >
            {(executionsQuery.data?.items ?? []).map((item) => (
              <div key={item.id}>{renderMobileCard(item)}</div>
            ))}
          </div>
        )
      ) : (
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
      )}
    </PageWrapper>
  );
};

export default AgentsHistory;
