import React from "react";
import { useParams, useNavigate, useOutletContext } from "react-router-dom";
import { Card, Descriptions, Table, Tag, Grid } from "antd";
import { useWorkPackages } from "@/features/work-packages/api/useWorkPackages";
import { useWBSElement } from "@/features/wbs-elements/api/useWBSElements";
import { formatCurrency } from "@/utils/formatters";
import type { ControlAccountRead } from "@/api/generated";
import { PageContent } from "@/components/layout";
import { EntityMetadataCard } from "@/components/common/EntityMetadataCard";

/** Status color map for work packages */
const WP_STATUS_COLOR_MAP: Record<string, string> = {
  open: "blue",
  in_progress: "orange",
  closed: "green",
};

interface OutletContext {
  ca: ControlAccountRead | undefined;
}

/**
 * ControlAccountOverview - Overview sub-page for Control Account detail.
 *
 * Displays CA metadata, linked WBS Element, Org Unit, and a table of
 * Work Packages belonging to this control account.
 */
export const ControlAccountOverview: React.FC = () => {
  const { projectId, controlAccountId } = useParams<{
    projectId: string;
    controlAccountId: string;
  }>();
  const navigate = useNavigate();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const { ca } = useOutletContext<OutletContext>();

  // Work packages for this control account
  const { data: wpData, isLoading: wpLoading } = useWorkPackages({
    control_account_id: controlAccountId,
  });
  const workPackages = wpData?.items || [];

  // Linked WBS element for display
  const { data: wbsElement } = useWBSElement(ca?.wbs_element_id || "");

  return (
    <PageContent>
      {/* Control Account Information */}
      <Card title="Control Account Information">
        <Descriptions
          column={isMobile ? 1 : 2}
          size="middle"
          bordered
          items={[
            {
              key: "name",
              label: "Name",
              children: ca?.name || "-",
            },
            {
              key: "code",
              label: "Code",
              children: ca?.code || "-",
            },
            {
              key: "description",
              label: "Description",
              children: ca?.description || "-",
              span: isMobile ? 1 : 2,
            },
            {
              key: "wbsElement",
              label: "WBS Element",
              children: wbsElement ? (
                <a
                  onClick={() =>
                    navigate(
                      `/projects/${projectId}/wbs-elements/${wbsElement.wbs_element_id}`
                    )
                  }
                  style={{ cursor: "pointer" }}
                >
                  {wbsElement.code} - {wbsElement.name}
                </a>
              ) : (
                ca?.wbs_element_name || "-"
              ),
            },
            {
              key: "orgUnit",
              label: "Organizational Unit",
              children: ca?.organizational_unit_name || "-",
            },
          ]}
        />
      </Card>

      {/* Work Packages Table */}
      <Card title="Work Packages">
        <Table
          dataSource={workPackages}
          rowKey="work_package_id"
          loading={wpLoading}
          pagination={{
            defaultPageSize: 10,
            showSizeChanger: true,
            pageSizeOptions: ["10", "20", "50", "100"],
            showTotal: (total) => `Total ${total} items`,
            position: ["bottomRight"],
          }}
          onRow={(record) => ({
            onClick: () =>
              navigate(`/projects/${projectId}/work-packages/${record.work_package_id}`),
            style: { cursor: "pointer" },
          })}
          columns={[
            {
              title: "Code",
              dataIndex: "code",
              key: "code",
              width: 120,
              sorter: (a, b) =>
                a.code.localeCompare(b.code, undefined, { numeric: true }),
            },
            {
              title: "Name",
              dataIndex: "name",
              key: "name",
              sorter: (a, b) => a.name.localeCompare(b.name),
            },
            {
              title: "Status",
              dataIndex: "status",
              key: "status",
              width: 130,
              render: (status: string) => (
                <Tag color={WP_STATUS_COLOR_MAP[status || "open"] || "default"}>
                  {status || "open"}
                </Tag>
              ),
            },
            {
              title: "Budget",
              dataIndex: "budget_amount",
              key: "budget_amount",
              width: 140,
              align: "right" as const,
              render: (val: string) => formatCurrency(val),
              sorter: (a, b) =>
                Number(a.budget_amount || 0) - Number(b.budget_amount || 0),
            },
          ]}
        />
      </Card>

      {/* Control Account metadata footer — standardized across entity pages */}
      {ca && (
        <EntityMetadataCard
          entityId={ca.control_account_id}
          entityIdLabel="Control Account ID"
          parentId={ca.wbs_element_id}
          parentLabel="WBS Element"
          parentValue={ca.wbs_element_name}
          createdAt={ca.created_at}
          updatedAt={ca.updated_at}
          createdBy={ca.created_by_name}
          validTime={ca.valid_time_formatted}
          cardId="control-account-metadata-card"
        />
      )}
    </PageContent>
  );
};
