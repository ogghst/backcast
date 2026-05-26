import { useMemo, useState } from "react";
import {
  Table,
  Button,
  Space,
  Tag,
  Popconfirm,
  Tooltip,
  Select,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  HistoryOutlined,
  LinkOutlined,
  CalendarOutlined,
  SwapOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { usePermission } from "@/hooks/usePermission";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { mapHistoryVersions } from "@/utils/versionHistory";
import { formatCurrency } from "@/utils/formatters";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import {
  useWorkPackages,
  useCreateWorkPackage,
  useUpdateWorkPackage,
  useDeleteWorkPackage,
  usePackageTypes,
} from "../api/useWorkPackages";
import type {
  WorkPackageRead,
  WorkPackageCreate,
  WorkPackageUpdate,
} from "../api/useWorkPackages";
import { WorkPackageModal } from "./WorkPackageModal";
import { WorkPackageSummaryCard } from "./WorkPackageSummaryCard";
import { WorkPackageBreakdownDrawer } from "./WorkPackageBreakdownDrawer";

const STATUS_COLORS: Record<string, string> = {
  open: "blue",
  closed: "default",
};

interface WorkPackagesTabProps {
  projectId: string;
}

export const WorkPackagesTab = ({ projectId }: WorkPackagesTabProps) => {
  const { spacing, colors, borderRadius, typography } = useThemeTokens();
  const { can } = usePermission();
  const currency = useProjectCurrency(projectId);
  const { data: packageTypeOptions } = usePackageTypes();

  // Build dynamic color lookup from API data
  const typeColors = useMemo(() => {
    const colors: Record<string, string> = {};
    (packageTypeOptions || []).forEach((pt) => {
      colors[pt.value] = pt.color;
    });
    return colors;
  }, [packageTypeOptions]);

  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPackage, setEditingPackage] =
    useState<WorkPackageRead | null>(null);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [historyPackageId, setHistoryPackageId] = useState<string | null>(null);
  const [breakdownDrawerOpen, setBreakdownDrawerOpen] = useState(false);
  const [breakdownPackage, setBreakdownPackage] =
    useState<WorkPackageRead | null>(null);
  const [typeFilter, setTypeFilter] = useState<string | null>(null);

  // Query work packages
  const { data: packagesData, isLoading } = useWorkPackages({
    project_id: projectId,
    package_type_id: typeFilter ?? undefined,
    page,
    perPage,
  });

  const packages = packagesData?.items || [];
  const total = packagesData?.total || 0;

  // Mutations
  const createMutation = useCreateWorkPackage();
  const updateMutation = useUpdateWorkPackage();
  const deleteMutation = useDeleteWorkPackage();

  // History query
  const { data: historyData, isLoading: historyLoading } = useEntityHistory({
    resource: "work-packages",
    entityId: historyPackageId,
    fetchFn: async (id) => {
      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/work-packages/{work_package_id}/history",
        path: { work_package_id: id },
        errors: { 422: "Validation Error" },
      }) as Promise<WorkPackageRead[]>;
    },
    enabled: historyDrawerOpen && !!historyPackageId,
  });

  const handleCreate = () => {
    setEditingPackage(null);
    setModalOpen(true);
  };

  const handleEdit = (wp: WorkPackageRead) => {
    setEditingPackage(wp);
    setModalOpen(true);
  };

  const handleDelete = async (wp: WorkPackageRead) => {
    await deleteMutation.mutateAsync({
      id: wp.work_package_id,
      projectId,
    });
  };

  const handleToggleStatus = async (wp: WorkPackageRead) => {
    const newStatus = wp.status === "open" ? "closed" : "open";
    await updateMutation.mutateAsync({
      id: wp.work_package_id,
      data: { status: newStatus },
    });
  };

  const handleModalOk = async (
    values: WorkPackageCreate | WorkPackageUpdate,
  ) => {
    if (editingPackage) {
      await updateMutation.mutateAsync({
        id: editingPackage.work_package_id,
        data: values as WorkPackageUpdate,
      });
    } else {
      await createMutation.mutateAsync(values as WorkPackageCreate);
    }
    setModalOpen(false);
    setEditingPackage(null);
  };

  const handleViewHistory = (wp: WorkPackageRead) => {
    setHistoryPackageId(wp.work_package_id);
    setHistoryDrawerOpen(true);
  };

  const handleViewBreakdowns = (wp: WorkPackageRead) => {
    setBreakdownPackage(wp);
    setBreakdownDrawerOpen(true);
  };

  const columns: ColumnsType<WorkPackageRead> = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      width: 200,
      ellipsis: true,
      render: (name: string, record) => (
        <Tooltip title={name}>
          <span style={{ fontWeight: typography.weights.medium }}>
            {name}
          </span>
          {record.external_event_id &&
            record.external_event_id !== record.name && (
              <span
                style={{
                  color: colors.textTertiary,
                  fontSize: typography.sizes.xs,
                  marginLeft: spacing.xs,
                }}
              >
                ({record.external_event_id})
              </span>
            )}
        </Tooltip>
      ),
    },
    {
      title: "Type",
      dataIndex: "package_type_id",
      key: "package_type_id",
      width: 140,
      render: (_: string, record: WorkPackageRead) => (
        <Tag color={typeColors[record.package_type_id] || "default"}>
          {record.package_type_name || record.package_type_code || "Unknown"}
        </Tag>
      ),
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 90,
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status] || "default"}>
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </Tag>
      ),
    },
    {
      title: "Date",
      dataIndex: "event_date_formatted",
      key: "event_date",
      width: 130,
      render: (dateFormatted: { formatted: string }) => {
        const val = dateFormatted?.formatted;
        return val && val !== "Unknown" ? val : "-";
      },
    },
    {
      title: "COQ Category",
      dataIndex: "coq_category",
      key: "coq_category",
      width: 140,
      render: (category: string | null) => {
        if (!category) return <span style={{ color: colors.textTertiary }}>-</span>;
        return (
          <Tag
            color={
              category === "conformance" ? colors.success : colors.error
            }
            style={{ textTransform: "capitalize" }}
          >
            {category}
          </Tag>
        );
      },
    },
    {
      title: "Planned Cost",
      dataIndex: "cost_impact",
      key: "cost_impact",
      width: 140,
      align: "right",
      render: (cost: string) => (
        <span
          style={{
            fontWeight: typography.weights.medium,
            color: colors.text,
          }}
        >
          {formatCurrency(Number(cost || 0), currency)}
        </span>
      ),
      sorter: (a, b) =>
        Number(a.cost_impact || 0) - Number(b.cost_impact || 0),
    },
    {
      title: "Schedule",
      dataIndex: "schedule_impact_days",
      key: "schedule_impact_days",
      width: 110,
      render: (days: number | null) => {
        if (!days || days === 0) {
          return <span style={{ color: colors.textTertiary }}>-</span>;
        }
        return (
          <span style={{ color: colors.error }}>
            <CalendarOutlined style={{ marginRight: spacing.xs }} />
            {days}d
          </span>
        );
      },
    },
    {
      title: "Actual",
      key: "actual_cost",
      width: 130,
      align: "right",
      render: (_, record) => {
        const planned = Number(record.cost_impact || 0);
        const actual = record.actual_cost;
        if (actual === null || actual === undefined) {
          return <span style={{ color: colors.textTertiary }}>-</span>;
        }
        const overBudget = actual > planned;
        return (
          <Tooltip
            title={`Planned: ${formatCurrency(planned, currency)} | Actual: ${formatCurrency(actual, currency)}`}
          >
            <span
              style={{
                fontWeight: typography.weights.medium,
                color: overBudget ? colors.error : colors.text,
              }}
            >
              {formatCurrency(actual, currency)}
            </span>
          </Tooltip>
        );
      },
    },
    {
      title: "",
      key: "allocations",
      width: 70,
      render: (_, record) => (
        <Tooltip title="View allocations">
          <LinkOutlined
            onClick={() => handleViewBreakdowns(record)}
            style={{ color: colors.primary, cursor: "pointer" }}
          />
        </Tooltip>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      width: 140,
      fixed: "right",
      render: (_, record) => (
        <Space size="small">
          {can("work-package-update") && (
            <Tooltip title={record.status === "open" ? "Close" : "Reopen"}>
              <Button
                type="text"
                icon={<SwapOutlined />}
                onClick={() => handleToggleStatus(record)}
                style={{ color: colors.textSecondary }}
              />
            </Tooltip>
          )}
          {can("work-package-update") && (
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              style={{ color: colors.primary }}
            />
          )}
          <Button
            type="text"
            icon={<HistoryOutlined />}
            onClick={() => handleViewHistory(record)}
            style={{ color: colors.info }}
          />
          {can("work-package-delete") && (
            <Popconfirm
              title="Delete Work Package"
              description="Are you sure you want to delete this work package?"
              onConfirm={() => handleDelete(record)}
              okText="Delete"
              okButtonProps={{ danger: true }}
              cancelText="Cancel"
            >
              <Button type="text" icon={<DeleteOutlined />} danger />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Summary Card — only for quality-related views */}
      {(typeFilter === null ||
        packageTypeOptions?.find((pt) => pt.value === typeFilter)?.is_quality) && <WorkPackageSummaryCard projectId={projectId} />}

      {/* Action Bar */}
      <div
        style={{
          marginBottom: spacing.md,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h2 style={{ margin: 0, fontSize: typography.sizes.lg }}>
          Work Packages
        </h2>
        {can("work-package-create") && (
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            Add Package
          </Button>
        )}
      </div>

      {/* Type Filter */}
      <div style={{ marginBottom: spacing.md }}>
        <Select
          placeholder="Filter by type"
          value={typeFilter ?? undefined}
          onChange={(value) => {
            setTypeFilter(value ?? null);
            setPage(1);
          }}
          options={(packageTypeOptions || []).map((opt) => ({
            label: opt.label,
            value: opt.value,
          }))}
          allowClear
          style={{ minWidth: 200 }}
        />
      </div>

      {/* Table */}
      <Table
        columns={columns}
        dataSource={packages}
        rowKey="work_package_id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize: perPage,
          total,
          showSizeChanger: true,
          showTotal: (t) => `Total ${t} packages`,
          onChange: (newPage, newPerPage) => {
            setPage(newPage);
            setPerPage(newPerPage || 10);
          },
        }}
        scroll={{ x: 1200 }}
        style={{
          borderRadius: borderRadius.lg,
        }}
      />

      {/* Create/Edit Modal */}
      <WorkPackageModal
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          setEditingPackage(null);
        }}
        onOk={handleModalOk}
        confirmLoading={
          createMutation.isPending || updateMutation.isPending
        }
        initialValues={editingPackage}
        projectId={projectId}
        currency={currency}
      />

      {/* History Drawer */}
      <VersionHistoryDrawer
        open={historyDrawerOpen}
        onClose={() => {
          setHistoryDrawerOpen(false);
          setHistoryPackageId(null);
        }}
        versions={mapHistoryVersions(historyData)}
        entityName="Work Package"
        isLoading={historyLoading}
      />

      {/* Breakdown Drawer */}
      <WorkPackageBreakdownDrawer
        open={breakdownDrawerOpen}
        onClose={() => {
          setBreakdownDrawerOpen(false);
          setBreakdownPackage(null);
        }}
        workPackageId={breakdownPackage?.work_package_id || null}
        name={breakdownPackage?.name}
        totalCost={Number(breakdownPackage?.cost_impact || 0)}
        currency={currency}
      />
    </div>
  );
};
