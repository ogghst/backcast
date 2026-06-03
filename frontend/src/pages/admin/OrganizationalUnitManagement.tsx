import { App, Button, Card, Space, Tag, Tree, theme } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  HistoryOutlined,
  ApartmentOutlined,
  NodeIndexOutlined,
} from "@ant-design/icons";
import { useState, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { OrgUnitTreeNode } from "@/features/organizational-units/utils/orgUnitTree";
import { createResourceHooks } from "@/hooks/useCrud";
import { OrganizationalUnitsService } from "@/api/generated";
import type {
  OrganizationalUnitRead,
  OrganizationalUnitCreate,
  OrganizationalUnitUpdate,
} from "@/api/generated";
import { Can } from "@/components/auth/Can";
import { OrganizationalUnitModal } from "@/features/organizational-units/components/OrganizationalUnitModal";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { useOrgUnitTree } from "@/features/organizational-units/hooks/useOrgUnitTree";
import { queryKeys as qk } from "@/api/queryKeys";

// Keep existing CRUD hooks using the generated API service
const organizationalUnitApi = {
  list: async (params?: {
    pagination?: { current?: number; pageSize?: number };
    search?: string;
    filters?: Record<string, unknown>;
    sortField?: string;
    sortOrder?: string;
  }) => {
    const { pagination, search, filters, sortField, sortOrder } = params || {};
    const page = pagination?.current || 1;
    const perPage = pagination?.pageSize || 20;

    let filterString: string | undefined;
    if (filters) {
      const filterParts: string[] = [];
      Object.entries(filters).forEach(([key, value]) => {
        if (
          value &&
          (Array.isArray(value) ? value.length > 0 : value !== undefined)
        ) {
          const values = Array.isArray(value) ? value : [value];
          filterParts.push(`${key}:${values.join(",")}`);
        }
      });
      filterString = filterParts.length > 0 ? filterParts.join(";") : undefined;
    }

    const serverSortOrder = sortOrder === "descend" ? "desc" : "asc";

    const res = await OrganizationalUnitsService.getOrganizationalUnits(
      page,
      perPage,
      search,
      filterString,
      sortField,
      serverSortOrder
    );

    return Array.isArray(res) ? res : res.items;
  },
  detail: (id: string) =>
    OrganizationalUnitsService.getOrganizationalUnit(id) as Promise<OrganizationalUnitRead>,
  create: (data: OrganizationalUnitCreate) =>
    OrganizationalUnitsService.createOrganizationalUnit(data) as Promise<OrganizationalUnitRead>,
  update: (id: string, data: OrganizationalUnitUpdate) =>
    OrganizationalUnitsService.updateOrganizationalUnit(id, data) as Promise<OrganizationalUnitRead>,
  delete: (id: string) =>
    OrganizationalUnitsService.deleteOrganizationalUnit(id),
};

const { useCreate, useUpdate, useDelete } = createResourceHooks<
  OrganizationalUnitRead,
  OrganizationalUnitCreate,
  OrganizationalUnitUpdate
>("organizational-units", organizationalUnitApi as never);

export const OrganizationalUnitManagement = () => {
  const { token } = theme.useToken();
  const queryClient = useQueryClient();
  const { treeData, items, flatMap, isLoading } = useOrgUnitTree();

  const invalidateTree = () =>
    queryClient.invalidateQueries({ queryKey: qk.organizationalUnits.tree });
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedDepartment, setSelectedDepartment] =
    useState<OrganizationalUnitRead | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  // Fetch version history
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory({
    resource: "organizational-units",
    entityId: selectedDepartment?.organizational_unit_id,
    fetchFn: (id) =>
      OrganizationalUnitsService.getOrganizationalUnitHistory(id),
    enabled: historyOpen,
  });

  const { mutateAsync: createDepartment } = useCreate({
    onSuccess: () => {
      invalidateTree();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateDepartment } = useUpdate({
    onSuccess: () => {
      invalidateTree();
      setModalOpen(false);
    },
  });

  const { mutate: deleteDepartment } = useDelete({
    onSuccess: () => {
      invalidateTree();
    },
  });

  const { modal } = App.useApp();

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this organizational unit?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteDepartment(id),
    });
  };

  // Build tree data with action buttons in title
  const enrichedTreeData = useMemo(() => {
    const enrich = (nodes: OrgUnitTreeNode[]): OrgUnitTreeNode[] =>
      nodes.map((node) => {
        const unit = flatMap.get(node.key as string);
        const title = unit ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: token.paddingSM,
              paddingRight: token.paddingXS,
            }}
          >
            <Space>
              <ApartmentOutlined style={{ color: token.colorPrimary }} />
              <span style={{ fontWeight: 500 }}>{unit.code}</span>
              <span style={{ color: token.colorTextSecondary }}>&mdash;</span>
              <span>{unit.name}</span>
              {!unit.is_active && <Tag color="red">Inactive</Tag>}
            </Space>
            <Space size={0}>
              <Can permission="organizational-unit-read">
                <Button
                  type="text"
                  size="small"
                  icon={<HistoryOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedDepartment(unit);
                    setHistoryOpen(true);
                  }}
                  title="View History"
                />
              </Can>
              <Can permission="organizational-unit-update">
                <Button
                  type="text"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedDepartment(unit);
                    setModalOpen(true);
                  }}
                  title="Edit"
                />
              </Can>
              <Can permission="organizational-unit-delete">
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(unit.organizational_unit_id);
                  }}
                  title="Delete"
                />
              </Can>
            </Space>
          </div>
        ) : (
          node.title
        );
        return {
          ...node,
          title,
          children: node.children ? enrich(node.children) : undefined,
        };
      });
    return enrich(treeData);
  // eslint-disable-next-line react-hooks/exhaustive-deps -- enrich uses stable refs only (flatMap, token, handleDelete)
  }, [treeData, flatMap, token]);

  // Auto-expand all on first load
  const allKeys = useMemo(
    () => items.map((item) => item.organizational_unit_id),
    [items]
  );

  return (
    <>
      <Card
        title={
          <Space>
            <NodeIndexOutlined />
            <span style={{ fontSize: token.fontSizeLG, fontWeight: "bold" }}>
              Organizational Unit Management
            </span>
          </Space>
        }
        extra={
          <Space>
            <Button
              onClick={() => setExpandedKeys(allKeys)}
              size="small"
            >
              Expand All
            </Button>
            <Button
              onClick={() => setExpandedKeys([])}
              size="small"
            >
              Collapse All
            </Button>
            <Can permission="organizational-unit-create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedDepartment(null);
                  setModalOpen(true);
                }}
              >
                Add Organizational Unit
              </Button>
            </Can>
          </Space>
        }
      >
        <Tree
          treeData={enrichedTreeData}
          showLine
          expandedKeys={expandedKeys}
          onExpand={(keys) => setExpandedKeys(keys)}
          defaultExpandAll
          blockNode
        />
      </Card>

      <OrganizationalUnitModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedDepartment) {
            await updateDepartment({
              id: selectedDepartment.organizational_unit_id,
              data: values,
            });
          } else {
            await createDepartment(values as OrganizationalUnitCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedDepartment}
        excludeIds={
          selectedDepartment
            ? new Set([selectedDepartment.organizational_unit_id])
            : undefined
        }
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={(historyVersions || []).map(
          (version: Record<string, unknown>, idx: number, arr: unknown[]) => ({
            id: `v${arr.length - idx}`,
            valid_from: (version.created_at as string) || new Date().toISOString(),
            transaction_time: new Date().toISOString(),
            changed_by: (version.created_by_name as string) || "System",
            changes: idx === 0 ? { created: "initial" } : { updated: "changed" },
          })
        )}
        entityName={`Organizational Unit: ${selectedDepartment?.name || ""}`}
        isLoading={historyLoading}
      />
    </>
  );
};
