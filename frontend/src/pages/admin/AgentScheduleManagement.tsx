/**
 * Agent Schedule Management Admin Page
 *
 * CRUD table for scheduled agents. Templated on MCPServerList: antd Card +
 * StandardTable + a create/edit Modal. Row actions: Run-now (trigger), Edit,
 * Delete; an inline Switch toggles is_active. The assistant name is resolved
 * from the shared assistants list (useAIAssistants), and the cron expression
 * is shown with a cronstrue human-readable sub-line.
 */

import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { App, Button, Card, Space, Switch, Tag, Tooltip, Typography, theme } from "antd";
import {
  CaretRightOutlined,
  DeleteOutlined,
  EditOutlined,
  HistoryOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import type { ColumnType } from "antd/es/table";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { useAIAssistants } from "@/features/ai/api/useAIAssistants";
import { AgentScheduleModal } from "@/features/ai/schedules/components/AgentScheduleModal";
import {
  useAgentSchedules,
  useCreateAgentSchedule,
  useDeleteAgentSchedule,
  useToggleAgentSchedule,
  useTriggerAgentSchedule,
  useUpdateAgentSchedule,
} from "@/features/ai/schedules/api/useAgentSchedules";
import cronstrue from "cronstrue";
import type {
  AgentScheduleCreate,
  AgentScheduleRead,
  AgentScheduleUpdate,
} from "@/api/generated";

const { Text } = Typography;

function cronPreview(expr: string): string | null {
  if (!expr) return null;
  try {
    return cronstrue.toString(expr, { use24HourTimeFormat: true });
  } catch {
    return null;
  }
}

function formatRelative(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export const AgentScheduleManagement = () => {
  const { tableParams, handleTableChange } = useTableParams<AgentScheduleRead>();
  const { token } = theme.useToken();
  const { typography } = useThemeTokens();
  const { modal, message } = App.useApp();
  const navigate = useNavigate();

  const [modalOpen, setModalOpen] = useState(false);
  const [selected, setSelected] = useState<AgentScheduleRead | null>(null);

  const { data: schedules, isLoading, refetch } = useAgentSchedules();
  const { data: assistants } = useAIAssistants(true);

  const assistantNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const a of assistants ?? []) map.set(a.id, a.name);
    return map;
  }, [assistants]);

  const { mutateAsync: createSchedule, isPending: isCreating } = useCreateAgentSchedule({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateSchedule, isPending: isUpdating } = useUpdateAgentSchedule({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: deleteSchedule } = useDeleteAgentSchedule({
    onSuccess: () => refetch(),
  });

  const { mutate: toggleSchedule } = useToggleAgentSchedule();

  const triggerSchedule = useTriggerAgentSchedule({
    onSuccess: (resp) => {
      message.success("Schedule run started");
      void resp;
    },
  });

  const handleDelete = (record: AgentScheduleRead) => {
    modal.confirm({
      title: `Delete "${record.name}"?`,
      content: "This action cannot be undone. Past runs and sessions are preserved.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteSchedule(record.id),
    });
  };

  const handleTrigger = (record: AgentScheduleRead) => {
    modal.confirm({
      title: `Run "${record.name}" now?`,
      content: "Starts an immediate agent execution using this schedule's prompt and assistant.",
      okText: "Run now",
      onOk: () => triggerSchedule.mutateAsync(record.id),
    });
  };

  const columns: ColumnType<AgentScheduleRead>[] = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      sorter: true,
      render: (name: string, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: typography.sizes.sm }}>
            {assistantNameById.get(record.assistant_config_id) ?? "Unknown assistant"}
          </Text>
        </Space>
      ),
    },
    {
      title: "Cron",
      dataIndex: "cron_expr",
      key: "cron_expr",
      render: (expr: string) => (
        <Space direction="vertical" size={0}>
          <Text code>{expr}</Text>
          {(() => {
            const preview = cronPreview(expr);
            return preview ? (
              <Text type="secondary" style={{ fontSize: typography.sizes.sm }}>
                {preview}
              </Text>
            ) : null;
          })()}
        </Space>
      ),
    },
    {
      title: "Timezone",
      dataIndex: "timezone",
      key: "timezone",
      width: 140,
      render: (tz: string) => <Tag>{tz}</Tag>,
    },
    {
      title: "Next run",
      dataIndex: "next_run_at",
      key: "next_run_at",
      width: 200,
      render: (iso: string | null) =>
        iso ? (
          <Text>{formatRelative(iso)}</Text>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: "Last run",
      dataIndex: "last_run_at",
      key: "last_run_at",
      width: 200,
      render: (iso: string | null) =>
        iso ? (
          <Text>{formatRelative(iso)}</Text>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: "Active",
      dataIndex: "is_active",
      key: "is_active",
      width: 90,
      render: (isActive: boolean, record) => (
        <Switch
          checked={isActive}
          aria-label="toggle schedule active"
          onChange={() => toggleSchedule(record.id)}
        />
      ),
    },
    {
      title: "Actions",
      key: "actions",
      width: 180,
      render: (_, record) => (
        <Space>
          <Tooltip title="Run now">
            <Button
              icon={<CaretRightOutlined />}
              onClick={() => handleTrigger(record)}
              loading={triggerSchedule.isPending}
              aria-label="run now"
            />
          </Tooltip>
          <Tooltip title="See runs">
            <Button
              type="text"
              size="small"
              icon={<HistoryOutlined />}
              onClick={() => navigate(`/agents-history?schedule=${record.id}`)}
              aria-label="see runs"
            />
          </Tooltip>
          <Tooltip title="Edit">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelected(record);
                setModalOpen(true);
              }}
              aria-label="edit"
            />
          </Tooltip>
          <Tooltip title="Delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
              aria-label="delete"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <PageWrapper>
      <Card
        title="Agent Schedules"
        style={{ marginBottom: token.marginMD }}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setSelected(null);
              setModalOpen(true);
            }}
          >
            New schedule
          </Button>
        }
      >
        <StandardTable<AgentScheduleRead>
          tableParams={tableParams}
          onChange={handleTableChange}
          loading={isLoading}
          dataSource={schedules || []}
          columns={columns}
          rowKey="id"
        />
      </Card>

      <AgentScheduleModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selected) {
            await updateSchedule({
              id: selected.id,
              data: values as AgentScheduleUpdate,
            });
          } else {
            await createSchedule(values as AgentScheduleCreate);
          }
        }}
        confirmLoading={selected ? isUpdating : isCreating}
        initialValues={selected}
      />
    </PageWrapper>
  );
};

export default AgentScheduleManagement;
