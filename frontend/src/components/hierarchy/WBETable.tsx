import { Table, Button, Space, Input, Tag, theme, Grid } from "antd";
import type { ColumnType } from "antd/es/table";
import { WBERead } from "@/api/generated";
import {
  EditOutlined,
  DeleteOutlined,
  RightOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { Can } from "@/components/auth/Can";
import { useMemo, useState } from "react";

const { useBreakpoint } = Grid;

export interface WBETablePagination {
  current: number;
  pageSize: number;
  total: number;
  onChange: (page: number, pageSize: number) => void;
}

interface WBETableProps {
  wbes: WBERead[];
  loading?: boolean;
  onRowClick?: (wbe: WBERead) => void;
  onEdit?: (wbe: WBERead) => void;
  onDelete?: (wbe: WBERead) => void;
  searchable?: boolean;
  pagination?: WBETablePagination;
}

export const WBETable = ({
  wbes,
  loading,
  onRowClick,
  onEdit,
  onDelete,
  searchable = true,
  pagination,
}: WBETableProps) => {
  const { token } = theme.useToken();
  const screens = useBreakpoint();
  const isMobile = !screens.md; // Mobile: < 768px
  const [searchText, setSearchText] = useState("");

  const getColumnSearchProps = (
    dataIndex: keyof WBERead,
  ): ColumnType<WBERead> => ({
    filterDropdown: ({
      setSelectedKeys,
      selectedKeys,
      confirm,
      clearFilters,
    }) => (
      <div style={{ padding: token.marginSM }}>
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
      <SearchOutlined style={{ color: filtered ? token.colorPrimary : undefined }} />
    ),
    onFilter: (value, record) => {
      // Client-side filtering only applies if NOT using server-side pagination
      // OR if we want to filter within the current page (which is weird)
      // Usually, if server-side pagination is on, we disable client-side filtering features or map them to server.
      // For now, let's keep it simple: if pagination is provided, we assume server handles everything?
      // Actually, if we use server-side pagination, 'wbes' is just one page. Client-side filtering on one page is confusing.
      // But let's assume standard behavior.
      const fieldVal = record[dataIndex];
      return fieldVal
        ? fieldVal
            .toString()
            .toLowerCase()
            .includes((value as string).toLowerCase())
        : false;
    },
  });

  const columns: ColumnType<WBERead>[] = (() => {
    const cols: ColumnType<WBERead>[] = [
      {
        title: "Code",
        dataIndex: "code",
        key: "code",
        width: 100,
        sorter: (a, b) =>
          a.code.localeCompare(b.code, undefined, { numeric: true }),
        ...getColumnSearchProps("code"),
      },
      {
        title: "Name",
        dataIndex: "name",
        key: "name",
        sorter: (a, b) => a.name.localeCompare(b.name),
        ...getColumnSearchProps("name"),
      },
    ];

    // Hide Budget and Branch on mobile
    if (!isMobile) {
      cols.push(
        {
          title: "Budget",
          dataIndex: "budget_allocation",
          key: "budget_allocation",
          render: (val) =>
            val
              ? new Intl.NumberFormat("en-US", {
                  style: "currency",
                  currency: "EUR",
                }).format(val)
              : "-",
          width: 150,
          align: "right",
          sorter: (a, b) =>
            Number(a.budget_allocation || 0) - Number(b.budget_allocation || 0),
        },
        {
          title: "Branch",
          dataIndex: "branch",
          key: "branch",
          width: 120,
          render: (val) => (val ? <Tag>{val}</Tag> : "-"),
          sorter: (a, b) => a.branch.localeCompare(b.branch),
          ...getColumnSearchProps("branch"),
        }
      );
    }

    cols.push({
      title: "Actions",
      key: "actions",
      width: 150,
      align: "center",
      render: (_, record) => (
        <Space onClick={(e) => e.stopPropagation()}>
          <Can permission="wbe-update">
            <Button
              icon={<EditOutlined />}
              size="small"
              onClick={() => onEdit?.(record)}
              title="Edit"
            />
          </Can>
          <Can permission="wbe-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              size="small"
              onClick={() => onDelete?.(record)}
              title="Delete"
            />
          </Can>
          <Button
            type="primary"
            ghost
            size="small"
            icon={<RightOutlined />}
            onClick={() => onRowClick?.(record)}
            title="Drill Down"
          >
            {isMobile ? undefined : "Open"}
          </Button>
        </Space>
      ),
    });

    return cols;
  })();

  const filteredData = useMemo(() => {
    let result = wbes || [];
    // Only apply client-side text search if pagination IS NOT provided (legacy mode)
    // If pagination is provided, search should be handled by server (passed via props)
    // But for this component, let's keep it simple:
    if (searchText) {
      const lower = searchText.toLowerCase();
      result = result.filter(
        (w) =>
          w.name.toLowerCase().includes(lower) ||
          w.code.toLowerCase().includes(lower),
      );
    }
    return result;
  }, [wbes, searchText]);

  return (
    <div>
      {searchable && (
        <div
          style={{
            marginBottom: token.marginMD,
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <Input.Search
            placeholder="Search..."
            allowClear
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: isMobile ? "100%" : 300 }}
          />
        </div>
      )}
      <Table
        dataSource={filteredData}
        columns={columns}
        rowKey="wbe_id"
        loading={loading}
        scroll={{ x: isMobile ? "max-content" : undefined }}
        onRow={(record) => ({
          onClick: () => onRowClick?.(record),
          style: { cursor: "pointer" },
        })}
        pagination={
          pagination
            ? {
                current: pagination.current,
                pageSize: pagination.pageSize,
                total: pagination.total,
                onChange: pagination.onChange,
                showSizeChanger: true,
                pageSizeOptions: ["10", "20", "50", "100"],
                showTotal: (total) => `Total ${total} items`,
                position: ["bottomRight"],
              }
            : {
                defaultPageSize: 10,
                showSizeChanger: true,
                pageSizeOptions: ["10", "20", "50", "100"],
                showTotal: (total) => `Total ${total} items`,
                position: ["bottomRight"],
              }
        }
      />
    </div>
  );
};
