import { Table, Button, Space, Input } from "antd";
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

interface WBETableProps {
  wbes: WBERead[];
  loading?: boolean;
  onRowClick?: (wbe: WBERead) => void;
  onEdit?: (wbe: WBERead) => void;
  onDelete?: (wbe: WBERead) => void;
  searchable?: boolean;
}

export const WBETable = ({
  wbes,
  loading,
  onRowClick,
  onEdit,
  onDelete,
  searchable = true,
}: WBETableProps) => {
  const [searchText, setSearchText] = useState("");

  const getColumnSearchProps = (
    dataIndex: keyof WBERead
  ): ColumnType<WBERead> => ({
    filterDropdown: ({
      setSelectedKeys,
      selectedKeys,
      confirm,
      clearFilters,
    }) => (
      <div style={{ padding: 8 }}>
        <Input
          placeholder={`Search ${dataIndex}`}
          value={selectedKeys[0]}
          onChange={(e) =>
            setSelectedKeys(e.target.value ? [e.target.value] : [])
          }
          onPressEnter={() => confirm()}
          style={{ width: 188, marginBottom: 8, display: "block" }}
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
      <SearchOutlined style={{ color: filtered ? "#1890ff" : undefined }} />
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

  const columns: ColumnType<WBERead>[] = [
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
      sorter: (a, b) => (a.budget_allocation || 0) - (b.budget_allocation || 0),
    },
    {
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
            Open
          </Button>
        </Space>
      ),
    },
  ];

  const filteredData = useMemo(() => {
    let result = wbes || [];
    if (searchText) {
      const lower = searchText.toLowerCase();
      result = result.filter(
        (w) =>
          w.name.toLowerCase().includes(lower) ||
          w.code.toLowerCase().includes(lower)
      );
    }
    return result;
  }, [wbes, searchText]);

  return (
    <div>
      {searchable && (
        <div
          style={{
            marginBottom: 16,
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <Input.Search
            placeholder="Search..."
            allowClear
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 300 }}
          />
        </div>
      )}
      <Table
        dataSource={filteredData}
        columns={columns}
        rowKey="wbe_id"
        loading={loading}
        onRow={(record) => ({
          onClick: () => onRowClick?.(record),
          style: { cursor: "pointer" },
        })}
        pagination={false}
        size="middle"
      />
    </div>
  );
};
