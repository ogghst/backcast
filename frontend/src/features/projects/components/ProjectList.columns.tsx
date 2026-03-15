/**
 * Column Definitions for ProjectList Table
 *
 * Extracted for better performance and maintainability.
 * Column definitions are memoized to prevent unnecessary re-renders.
 */

import { Button, Input, Space, theme } from "antd";
import {
  HistoryOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useMemo } from "react";
import type { ColumnType } from "antd/es/table";
import type { ProjectRead } from "@/types";
import { Can } from "@/components/auth/Can";

/**
 * Get column search props for table filtering
 */
export const getColumnSearchProps = (
  dataIndex: keyof ProjectRead,
): ColumnType<ProjectRead> => {
  const { token } = theme.useToken();

  return {
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
  };
};

/**
 * Memoized status filter options
 */
export const useStatusFilters = () =>
  useMemo(
    () => [
      { text: "Draft", value: "Draft" },
      { text: "Active", value: "Active" },
      { text: "Completed", value: "Completed" },
      { text: "On Hold", value: "On Hold" },
    ],
    [],
  );

/**
 * Memoized currency formatter for budget columns
 */
export const useCurrencyFormatter = () =>
  useMemo(
    () =>
      new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "EUR",
        currencyDisplay: "narrowSymbol",
      }),
    [],
  );

/**
 * Memoized date formatter for date columns
 */
export const useDateFormatter = () =>
  useMemo(
    () => (date: string) => (date ? new Date(date).toLocaleDateString() : "-"),
    [],
  );

/**
 * Build project table columns
 */
export const useProjectColumns = ({
  onViewHistory,
  onEdit,
  onDelete,
}: {
  onViewHistory: (project: ProjectRead) => void;
  onEdit: (project: ProjectRead) => void;
  onDelete: (projectId: string) => void;
}) => {
  const statusFilters = useStatusFilters();
  const formatCurrency = useCurrencyFormatter();
  const formatDate = useDateFormatter();

  return useMemo<ColumnType<ProjectRead>[]>(
    () => [
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
          budget ? formatCurrency.format(budget) : "-",
        width: 150,
        sorter: true,
      },
      {
        title: "Contract Value",
        dataIndex: "contract_value",
        key: "contract_value",
        render: (value: number) => (value ? formatCurrency.format(value) : "-"),
        width: 150,
        sorter: true,
      },
      {
        title: "Start Date",
        dataIndex: "start_date",
        key: "start_date",
        render: formatDate,
        width: 120,
        sorter: true,
      },
      {
        title: "End Date",
        dataIndex: "end_date",
        key: "end_date",
        render: formatDate,
        width: 120,
        sorter: true,
      },
      {
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
                  onViewHistory(record);
                }}
                title="View History"
              />
            </Can>
            <Can permission="project-update">
              <Button
                icon={<EditOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(record);
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
                  onDelete(record.project_id);
                }}
                title="Delete Project"
              />
            </Can>
          </Space>
        ),
      },
    ],
    [
      statusFilters,
      formatCurrency,
      formatDate,
      onViewHistory,
      onEdit,
      onDelete,
    ],
  );
};
