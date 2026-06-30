import React from "react";
import { useParams, useNavigate, useOutletContext } from "react-router-dom";
import { useState } from "react";
import { Button, Descriptions, Table, Tag, Grid } from "antd";
import { HistoryOutlined, InfoCircleOutlined, ProfileOutlined } from "@ant-design/icons";
import { PanelCard } from "@/components/common/PanelCard";
import { useWorkPackages } from "@/features/work-packages/api/useWorkPackages";
import { useWBSElement } from "@/features/wbs-elements/api/useWBSElements";
import { formatCurrency } from "@/utils/formatters";
import { ControlAccountsService, type ControlAccountRead } from "@/api/generated";
import { PageContent } from "@/components/layout";
import { EntityMetadataCard } from "@/components/common/EntityMetadataCard";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { Can } from "@/components/auth/Can";

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

  // Version history state
  const [historyOpen, setHistoryOpen] = useState(false);
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory({
    resource: "control-accounts",
    entityId: controlAccountId,
    fetchFn: (id) => ControlAccountsService.getControlAccountHistory(id),
    enabled: historyOpen,
  });

  return (
    <PageContent>
      {/* Control Account Information */}
      <PanelCard
        icon={<InfoCircleOutlined />}
        title="Control Account Information"
      >
        <Descriptions
          column={1}
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
      </PanelCard>

      {/* Work Packages Table */}
      <PanelCard
        icon={<ProfileOutlined />}
        title="Work Packages"
      >
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
      </PanelCard>

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
          extra={
            <Can permission="control-account-read">
              <Button
                icon={<HistoryOutlined />}
                onClick={() => setHistoryOpen(true)}
              >
                {isMobile ? undefined : "History"}
              </Button>
            </Can>
          }
        />
      )}

      {/* Version history drawer */}
      {ca && (
        <VersionHistoryDrawer
          open={historyOpen}
          onClose={() => setHistoryOpen(false)}
          entityName={`CA: ${ca.code || ""} - ${ca.name}`}
          isLoading={historyLoading}
          versions={(historyVersions || []).map((version: Record<string, unknown>, idx: number, arr: unknown[]) => {
            const validTimeFormatted = version.valid_time_formatted as {
              lower: string | null;
              upper: string | null;
              lower_formatted: string;
              upper_formatted: string;
              is_currently_valid: boolean;
            } | undefined;
            const transactionTimeFormatted = version.transaction_time_formatted as {
              lower: string | null;
              upper: string | null;
              lower_formatted: string;
              upper_formatted: string;
              is_currently_valid: boolean;
            } | undefined;

            return {
              id: `v${arr.length - idx}`,
              valid_from: validTimeFormatted?.lower || "",
              valid_to: validTimeFormatted?.upper || null,
              transaction_time: transactionTimeFormatted?.lower || "",
              changed_by: (version.created_by_name as string) || "System",
              valid_time_formatted: validTimeFormatted,
              transaction_time_formatted: transactionTimeFormatted,
            };
          })}
        />
      )}
    </PageContent>
  );
};
