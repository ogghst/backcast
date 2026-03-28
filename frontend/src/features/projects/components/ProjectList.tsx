import { App, Button, Empty, Grid, Input, List, Space, Spin, theme } from "antd";
import { useNavigate } from "react-router-dom";
import {
  HistoryOutlined,
  ProjectOutlined,
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useMemo, useState } from "react";
import type { ColumnType } from "antd/es/table";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import type {
  ProjectRead,
  ProjectCreate,
  ProjectUpdate,
} from "@/api/generated";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { Can } from "@/components/auth/Can";
import { ProjectModal } from "./ProjectModal";
import { ProjectCard } from "./ProjectCard";
import {
  useProjects,
  useCreateProject,
  useUpdateProject,
  useDeleteProject,
} from "../api/useProjects";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { ProjectFilters } from "@/types/filters";
import { ProjectsService } from "@/api/generated";

const { useBreakpoint } = Grid;

export const ProjectList = () => {
  const { token } = theme.useToken();
  const navigate = useNavigate();
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const isTablet = screens.md && !screens.lg;

  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    ProjectRead,
    ProjectFilters
  >();
  const { data, isLoading, refetch } = useProjects(tableParams);
  const projects = data?.items || [];
  const total = data?.total || 0;

  const [historyOpen, setHistoryOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState<ProjectRead | null>(
    null
  );

  const { modal } = App.useApp();

  const { mutateAsync: createProject } = useCreateProject({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateProject } = useUpdateProject({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: deleteProject } = useDeleteProject({
    onSuccess: () => refetch(),
  });

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this project?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteProject(id),
    });
  };

  const handleEdit = (project: ProjectRead) => {
    setSelectedProject(project);
    setModalOpen(true);
  };

  const handleViewHistory = (project: ProjectRead) => {
    setSelectedProject(project);
    setHistoryOpen(true);
  };

  const getColumnSearchProps = (
    dataIndex: keyof ProjectRead
  ): ColumnType<ProjectRead> => ({
    filterDropdown: ({
      setSelectedKeys,
      selectedKeys,
      confirm,
      clearFilters,
    }) => (
      <div style={{ padding: token.paddingSM }}>
        <Input
          placeholder={`Search ${dataIndex}`}
          value={selectedKeys[0]}
          onChange={(e) =>
            setSelectedKeys(e.target.value ? [e.target.value] : [])
          }
          onPressEnter={() => confirm()}
          style={{ width: 188, marginBottom: token.marginSM, display: "block" }}
        />
        <Space>
          <Button
            type="primary"
            onClick={() => confirm()}
            icon={<SearchOutlined />}
            size="small"
            style={{ width: 90 }}
          >
            Search
          </Button>
          <Button
            onClick={() => clearFilters && clearFilters()}
            size="small"
            style={{ width: 90 }}
          >
            Reset
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined
        style={{ color: filtered ? token.colorPrimary : undefined }}
      />
    ),
    onFilter: (value, record) => {
      const fieldVal = record[dataIndex];
      return fieldVal
        ? fieldVal
            .toString()
            .toLowerCase()
            .includes((value as string).toLowerCase())
        : false;
    },
  });

  // Extract unique status values for filter dropdown
  const statusFilters = useMemo(() => {
    // Common project statuses - could be fetched from API in the future
    return [
      { text: "Draft", value: "Draft" },
      { text: "Active", value: "Active" },
      { text: "Completed", value: "Completed" },
      { text: "On Hold", value: "On Hold" },
    ];
  }, []);

  const columns: ColumnType<ProjectRead>[] = (() => {
    const cols: ColumnType<ProjectRead>[] = [
      {
        title: "Code",
        dataIndex: "code",
        key: "code",
        width: 120,
        sorter: true,
        ...getColumnSearchProps("code"),
      },
      {
        title: "Name",
        dataIndex: "name",
        key: "name",
        sorter: true,
        ...getColumnSearchProps("name"),
      },
      {
        title: "Status",
        dataIndex: "status",
        key: "status",
        width: 120,
        filters: statusFilters,
      },
      {
        title: "Budget",
        dataIndex: "budget",
        key: "budget",
        render: (budget: number) =>
          budget
            ? new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: "EUR",
                currencyDisplay: "narrowSymbol",
              }).format(budget)
            : "-",
        width: 150,
        sorter: true,
      },
    ];

    // Hide Contract Value and dates on tablet
    if (!isTablet) {
      cols.push(
        {
          title: "Contract Value",
          dataIndex: "contract_value",
          key: "contract_value",
          render: (value: number) =>
            value
              ? new Intl.NumberFormat("en-US", {
                  style: "currency",
                  currency: "EUR",
                  currencyDisplay: "narrowSymbol",
                }).format(value)
              : "-",
          width: 150,
          sorter: true,
        },
        {
          title: "Start Date",
          dataIndex: "start_date",
          key: "start_date",
          render: (date: string) =>
            date ? new Date(date).toLocaleDateString() : "-",
          width: 120,
          sorter: true,
        },
        {
          title: "End Date",
          dataIndex: "end_date",
          key: "end_date",
          render: (date: string) =>
            date ? new Date(date).toLocaleDateString() : "-",
          width: 120,
          sorter: true,
        }
      );
    }

    cols.push({
      title: "Actions",
      key: "actions",
      width: 120,
      render: (_, record) => (
        <Space>
          <Can permission="project-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                handleViewHistory(record);
              }}
              title="View History"
            />
          </Can>
          <Can permission="project-update">
            <Button
              icon={<EditOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                handleEdit(record);
              }}
              title="Edit Project"
            />
          </Can>
          <Can permission="project-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                handleDelete(record.project_id);
              }}
              title="Delete Project"
            />
          </Can>
        </Space>
      ),
    });

    return cols;
  })();

  const toolbarContent = (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <div
        style={{
          fontSize: token.fontSizeLG,
          fontWeight: "bold",
          display: "flex",
          alignItems: "center",
          gap: token.marginSM,
        }}
      >
        <ProjectOutlined />
        Projects
      </div>
      <Can permission="project-create">
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setSelectedProject(null);
            setModalOpen(true);
          }}
        >
          {isMobile ? null : "Add Project"}
        </Button>
      </Can>
    </div>
  );

  return (
    <div>
      {isMobile ? (
        <MobileProjectList
          projects={projects}
          isLoading={isLoading}
          searchValue={tableParams.search || ""}
          onSearch={handleSearch}
          toolbar={toolbarContent}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onViewHistory={handleViewHistory}
          total={total}
          pagination={tableParams.pagination}
          onPageChange={(page, pageSize) =>
            handleTableChange(
              { current: page, pageSize },
              {},
              {}
            )
          }
        />
      ) : (
        <StandardTable<ProjectRead>
          tableParams={{
            ...tableParams,
            pagination: { ...tableParams.pagination, total },
          }}
          onChange={handleTableChange}
          loading={isLoading}
          dataSource={projects}
          columns={columns}
          rowKey="project_id"
          searchable={true}
          searchPlaceholder="Search projects..."
          onSearch={handleSearch}
          onRow={(record) => ({
            onClick: () => navigate(`/projects/${record.project_id}`),
            style: { cursor: "pointer" },
          })}
          toolbar={toolbarContent}
        />
      )}

      <ProjectModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedProject) {
            await updateProject({
              id: selectedProject.project_id,
              data: values as ProjectUpdate,
            });
          } else {
            await createProject(values as ProjectCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedProject}
      />

      <HistoryDrawerWrapper
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        project={selectedProject}
      />
    </div>
  );
};

const HistoryDrawerWrapper = ({
  open,
  onClose,
  project,
}: {
  open: boolean;
  onClose: () => void;
  project: ProjectRead | null;
}) => {
  const { data: history, isLoading } = useEntityHistory({
    resource: "projects",
    entityId: project?.project_id,
    fetchFn: (id) => ProjectsService.getProjectHistory(id),
    enabled: open,
  });

  return (
    <VersionHistoryDrawer
      open={open}
      onClose={onClose}
      versions={(history || []).map((v, idx, arr) => ({
        ...v,
        id: `v${arr.length - idx}`,
        valid_from: Array.isArray(v.valid_time)
          ? v.valid_time[0]
          : (v.valid_time as unknown as string) || new Date().toISOString(),
        transaction_time: Array.isArray(v.transaction_time)
          ? v.transaction_time[0]
          : (v.transaction_time as unknown as string) ||
            new Date().toISOString(),
        changed_by: v.created_by_name || "System",
      }))}
      entityName={`Project: ${project?.name || ""}`}
      isLoading={isLoading}
    />
  );
};

const MobileProjectList = ({
  projects,
  isLoading,
  searchValue,
  onSearch,
  toolbar,
  onEdit,
  onDelete,
  onViewHistory,
  total,
  pagination,
  onPageChange,
}: {
  projects: ProjectRead[];
  isLoading: boolean;
  searchValue: string;
  onSearch: (value: string) => void;
  toolbar: React.ReactNode;
  onEdit: (project: ProjectRead) => void;
  onDelete: (projectId: string) => void;
  onViewHistory: (project: ProjectRead) => void;
  total: number;
  pagination?: { current?: number; pageSize?: number };
  onPageChange: (page: number, pageSize: number) => void;
}) => {
  const { token } = theme.useToken();
  const [localSearch, setLocalSearch] = useState(searchValue);

  // Debounced search
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<
    typeof setTimeout
  > | null>(null);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalSearch(val);
    if (debounceTimer) clearTimeout(debounceTimer);
    setDebounceTimer(setTimeout(() => onSearch(val), 300));
  };

  return (
    <div>
      {/* Toolbar */}
      <div style={{ marginBottom: token.marginMD }}>{toolbar}</div>

      {/* Search */}
      <Input.Search
        placeholder="Search projects..."
        allowClear
        value={localSearch}
        onChange={handleSearchChange}
        onSearch={onSearch}
        style={{ marginBottom: token.marginMD }}
      />

      {/* Card list */}
      {isLoading ? (
        <div style={{ textAlign: "center", padding: token.paddingXL }}>
          <Spin />
        </div>
      ) : projects.length === 0 ? (
        <Empty description="No projects found" />
      ) : (
        <List
          grid={{ gutter: 12, column: 1 }}
          dataSource={projects}
          renderItem={(project) => (
            <List.Item>
              <ProjectCard
                project={project}
                onEdit={onEdit}
                onDelete={onDelete}
                onViewHistory={onViewHistory}
              />
            </List.Item>
          )}
          pagination={
            total > (pagination?.pageSize || 10)
              ? {
                  current: pagination?.current || 1,
                  pageSize: pagination?.pageSize || 10,
                  total,
                  onChange: onPageChange,
                  size: "small",
                  style: { textAlign: "center", marginTop: 16 },
                }
              : undefined
          }
        />
      )}
    </div>
  );
};
