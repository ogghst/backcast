import { useMemo, useState } from "react";
import { App, Button, Card, Space, Tag } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  HistoryOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import type { ColumnType } from "antd/es/table";
import type {
  CustomEntityTemplateCreate,
  CustomEntityTemplateRead,
  CustomEntityTemplateUpdate,
} from "@/api/generated";
import { Can } from "@/components/auth/Can";
import { StandardTable } from "@/components/common/StandardTable";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { useTableParams } from "@/hooks/useTableParams";
import { getErrorMessage } from "@/utils/apiError";
import { useOrgUnitTree } from "@/features/organizational-units/hooks/useOrgUnitTree";
import type { CustomEntityTemplateFilters } from "@/types/filters";
import { CustomEntityTemplateModal } from "@/features/custom-fields/components/CustomEntityTemplateModal";
import {
  useCreateCustomEntityTemplate,
  useCustomEntityTemplateHistory,
  useCustomEntityTemplates,
  useDeleteCustomEntityTemplate,
  useUpdateCustomEntityTemplate,
} from "@/features/custom-fields/api/useCustomEntityTemplates";

const TARGET_ENTITY_LABELS: Record<string, string> = {
  PROJECT: "Project",
  WBS_ELEMENT: "WBS Element",
  WORK_PACKAGE: "Work Package",
  CHANGE_ORDER: "Change Order",
};

export const CustomEntityTemplateManagement = () => {
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    CustomEntityTemplateRead,
    CustomEntityTemplateFilters
  >();

  const { data: templates = [], isLoading } = useCustomEntityTemplates();
  const { pathMap } = useOrgUnitTree();

  const [modalOpen, setModalOpen] = useState(false);
  const [selected, setSelected] = useState<CustomEntityTemplateRead | null>(
    null,
  );
  const [historyOpen, setHistoryOpen] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const { mutateAsync: createTemplate, isPending: createPending } =
    useCreateCustomEntityTemplate();
  const { mutateAsync: updateTemplate, isPending: updatePending } =
    useUpdateCustomEntityTemplate();
  const { mutate: deleteTemplate } = useDeleteCustomEntityTemplate();

  const { data: historyVersions, isLoading: historyLoading } =
    useCustomEntityTemplateHistory(selected?.custom_entity_template_id, historyOpen);

  const { modal } = App.useApp();

  const openCreate = () => {
    setSelected(null);
    setSubmitError(null);
    setModalOpen(true);
  };

  const openEdit = (record: CustomEntityTemplateRead) => {
    setSelected(record);
    setSubmitError(null);
    setModalOpen(true);
  };

  const handleSubmit = async (
    values: CustomEntityTemplateCreate | CustomEntityTemplateUpdate,
  ) => {
    setSubmitError(null);
    try {
      if (selected) {
        await updateTemplate({
          id: selected.custom_entity_template_id,
          data: values as CustomEntityTemplateUpdate,
        });
      } else {
        await createTemplate(values as CustomEntityTemplateCreate);
      }
      setModalOpen(false);
    } catch (error) {
      // Backend rejects malformed field_definitions / immutable
      // target_entity_type with HTTP 400 detail string. Surface it inline.
      setSubmitError(getErrorMessage(error));
    }
  };

  const handleDelete = (record: CustomEntityTemplateRead) => {
    modal.confirm({
      title: "Are you sure you want to delete this custom entity template?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteTemplate(record.custom_entity_template_id),
    });
  };

  const columns: ColumnType<CustomEntityTemplateRead>[] = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      sorter: true,
    },
    {
      title: "Code",
      dataIndex: "code",
      key: "code",
      render: (code: string) => <Tag>{code}</Tag>,
    },
    {
      title: "Target Entity",
      dataIndex: "target_entity_type",
      key: "target_entity_type",
      render: (t: string) => TARGET_ENTITY_LABELS[t] ?? t,
    },
    {
      title: "Organizational Unit",
      dataIndex: "organizational_unit_id",
      key: "organizational_unit_id",
      render: (id: string) => pathMap.get(id) || id,
    },
    {
      title: "Fields",
      key: "field_count",
      align: "center",
      render: (_: unknown, record: CustomEntityTemplateRead) => {
        const count = record.field_definitions
          ? Object.keys(record.field_definitions).length
          : 0;
        return <Tag color={count > 0 ? "blue" : undefined}>{count}</Tag>;
      },
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, record: CustomEntityTemplateRead) => (
        <Space>
          <Can permission="custom-entity-template-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => {
                setSelected(record);
                setHistoryOpen(true);
              }}
              title="View History"
            />
          </Can>
          <Can permission="custom-entity-template-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => openEdit(record)}
              title="Edit Template"
            />
          </Can>
          <Can permission="custom-entity-template-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
              title="Delete Template"
            />
          </Can>
        </Space>
      ),
    },
  ];

  // Client-side search over the already-fetched list (mirrors the search
  // affordance of CostElementTypeManagement for this lightweight admin page).
  const filtered = useMemo(() => {
    const term = (tableParams.search || "").trim().toLowerCase();
    if (!term) return templates;
    return templates.filter((t) => {
      return (
        t.name?.toLowerCase().includes(term) ||
        t.code?.toLowerCase().includes(term)
      );
    });
  }, [templates, tableParams.search]);

  return (
    <PageWrapper>
      <Card
        title="Custom Entity Templates"
        extra={
          <Can permission="custom-entity-template-create">
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={openCreate}
            >
              Add Template
            </Button>
          </Can>
        }
      >
        <StandardTable<CustomEntityTemplateRead>
          tableParams={tableParams}
          onChange={handleTableChange}
          loading={isLoading}
          dataSource={filtered}
          columns={columns}
          rowKey="custom_entity_template_id"
          searchable={true}
          onSearch={handleSearch}
        />
      </Card>

      <CustomEntityTemplateModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={createPending || updatePending}
        initialValues={selected}
        submitError={submitError}
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={(historyVersions || []).map((version, idx, arr) => {
          const v = version as unknown as CustomEntityTemplateRead & {
            created_at?: string;
            created_by_name?: string;
          };
          return {
            id: `v${arr.length - idx}`,
            valid_from: v.created_at || new Date().toISOString(),
            transaction_time: new Date().toISOString(),
            changed_by: v.created_by_name || "System",
            changes: idx === 0 ? { created: "initial" } : { updated: "changed" },
          };
        })}
        entityName={`Template: ${selected?.name || ""}`}
        isLoading={historyLoading}
      />
    </PageWrapper>
  );
};
