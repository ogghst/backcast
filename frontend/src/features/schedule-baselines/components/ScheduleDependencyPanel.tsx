/**
 * Schedule Dependency Panel
 *
 * Collapsible table embedded below the Gantt chart for managing
 * dependency links between schedule baselines. Provides CRUD operations
 * via modal and displays date conflict warnings.
 *
 * @module features/schedule-baselines/components
 */

import { useState, useMemo } from "react";
import { Card, Table, Button, Tag, Space, Popconfirm, theme, Typography, message } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import {
  useScheduleDependencies,
  useDeleteScheduleDependency,
  type ScheduleDependencyRead,
  type ScheduleOption,
  formatScheduleLabel,
} from "../api/useScheduleDependencies";
import { ScheduleDependencyModal } from "./ScheduleDependencyModal";
import { ScheduleDependencyWarnings } from "./ScheduleDependencyWarnings";

const { Text } = Typography;

const DEPENDENCY_TYPE_COLORS: Record<string, string> = {
  FS: "blue",
  SS: "green",
  FF: "orange",
  SF: "purple",
};

interface ScheduleDependencyPanelProps {
  projectId: string;
  schedules: ScheduleOption[];
}

export const ScheduleDependencyPanel: React.FC<ScheduleDependencyPanelProps> = ({
  projectId,
  schedules,
}) => {
  const { token } = theme.useToken();
  const [modalOpen, setModalOpen] = useState(false);
  const [editDependency, setEditDependency] = useState<ScheduleDependencyRead | null>(null);

  const { data: dependencies = [], isLoading } = useScheduleDependencies(projectId);
  const deleteMutation = useDeleteScheduleDependency();

  // Map for ID -> name lookup
  const scheduleNameMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of schedules) {
      map.set(s.schedule_baseline_id, formatScheduleLabel(s));
    }
    return map;
  }, [schedules]);

  const handleAdd = () => {
    setEditDependency(null);
    setModalOpen(true);
  };

  const handleEdit = (dep: ScheduleDependencyRead) => {
    setEditDependency(dep);
    setModalOpen(true);
  };

  const handleDelete = async (scheduleDependencyId: string) => {
    try {
      await deleteMutation.mutateAsync(scheduleDependencyId);
    } catch {
      message.error("Failed to delete dependency.");
    }
  };

  const handleModalClose = () => {
    setModalOpen(false);
    setEditDependency(null);
  };

  const columns = [
    {
      title: "Predecessor",
      dataIndex: "predecessor_id",
      key: "predecessor_id",
      render: (id: string) => (
        <Text>{scheduleNameMap.get(id) ?? id}</Text>
      ),
    },
    {
      title: "Successor",
      dataIndex: "successor_id",
      key: "successor_id",
      render: (id: string) => (
        <Text>{scheduleNameMap.get(id) ?? id}</Text>
      ),
    },
    {
      title: "Type",
      dataIndex: "dependency_type",
      key: "dependency_type",
      width: 100,
      render: (type: string) => (
        <Tag color={DEPENDENCY_TYPE_COLORS[type] ?? "default"}>{type}</Tag>
      ),
    },
    {
      title: "Lag (days)",
      dataIndex: "lag_days",
      key: "lag_days",
      width: 100,
      render: (lag: number) => (
        <Text type={lag < 0 ? "warning" : undefined}>{lag}</Text>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      width: 120,
      render: (_: unknown, record: ScheduleDependencyRead) => (
        <Space size={token.marginXXS}>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="Delete this dependency?"
            onConfirm={() => handleDelete(record.schedule_dependency_id)}
            okText="Delete"
            cancelText="Cancel"
          >
            <Button
              type="text"
              size="small"
              icon={<DeleteOutlined />}
              danger
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <ScheduleDependencyWarnings
        dependencies={dependencies}
        schedules={schedules}
      />
      <Card
        title="Schedule Dependencies"
        size="small"
        styles={{ body: { padding: 0 } }}
        extra={
          <Button
            type="primary"
            size="small"
            icon={<PlusOutlined />}
            onClick={handleAdd}
          >
            Add
          </Button>
        }
      >
        <Table
          dataSource={dependencies}
          columns={columns}
          rowKey="schedule_dependency_id"
          loading={isLoading}
          size="small"
          pagination={dependencies.length > 10 ? { pageSize: 10 } : false}
        />
      </Card>

      <ScheduleDependencyModal
        open={modalOpen}
        projectId={projectId}
        editDependency={editDependency}
        schedules={schedules}
        onClose={handleModalClose}
      />
    </>
  );
};
