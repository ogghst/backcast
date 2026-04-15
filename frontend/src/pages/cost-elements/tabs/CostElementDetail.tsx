import { useState } from "react";
import {
  Descriptions,
  Progress,
  Button,
  Grid,
  Typography,
  theme,
} from "antd";
import { EditOutlined } from "@ant-design/icons";
import type { CostElementRead } from "@/api/generated";
import {
  useBudgetStatus,
  useProjectBudgetSettings,
} from "@/features/cost-registration/api/useCostRegistrations";
import { useWBE } from "@/features/wbes/api/useWBEs";
import {
  useUpdateCostElement,
  useCostElementForecast,
} from "@/features/cost-elements/api/useCostElements";
import { CostElementModal } from "@/features/cost-elements/components/CostElementModal";
// import { EVMTimeHistoryChart } from "@/features/cost-elements/components/EVMTimeHistoryChart";
import { ForecastComparisonCard } from "@/features/forecasts/components";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import { formatRangeDate } from "@/utils/temporal";

interface CostElementDetailProps {
  costElement: CostElementRead;
}

const { useBreakpoint } = Grid;
const { Text } = Typography;

export const CostElementDetail = ({ costElement }: CostElementDetailProps) => {
  const screens = useBreakpoint();
  const { token } = theme.useToken();
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const queryClient = useQueryClient();
  const { branch, asOf } = useTimeMachineParams();
  const currentBranch = branch || costElement.branch || "main";
  const isMobile = !screens.md;
  const isSmallMobile = screens.xs;

  const { data: budgetStatus, isLoading } = useBudgetStatus(
    costElement.cost_element_id,
  );

  // Fetch WBE to get project_id for budget settings
  const { data: wbe } = useWBE(costElement.wbe_id);

  // Fetch project budget settings to get warning threshold
  const { data: projectBudgetSettings } = useProjectBudgetSettings(
    wbe?.project_id || "",
  );

  // Fetch forecast for this cost element (1:1 relationship)
  useCostElementForecast(costElement.cost_element_id);

  const updateMutation = useUpdateCostElement({
    onSuccess: () => {
      // Invalidate cost element detail with Time Machine context
      queryClient.invalidateQueries({
        queryKey: queryKeys.costElements.detail(costElement.cost_element_id, {
          branch: currentBranch,
          asOf,
        }),
      });
      // Invalidate breadcrumb
      queryClient.invalidateQueries({
        queryKey: queryKeys.costElements.breadcrumb(
          costElement.cost_element_id,
        ),
      });
      // Invalidate budget status with Time Machine context
      queryClient.invalidateQueries({
        queryKey: queryKeys.costRegistrations.budgetStatus(
          costElement.cost_element_id,
          { asOf },
        ),
      });
      // Invalidate forecast for this cost element (1:1 relationship)
      queryClient.invalidateQueries({
        queryKey: queryKeys.forecasts.byCostElement(
          costElement.cost_element_id,
          currentBranch,
          { asOf },
        ),
      });
      setIsEditModalOpen(false);
    },
  });

  const budget = budgetStatus?.budget
    ? Number(budgetStatus.budget)
    : Number(costElement.budget_amount);
  const used = budgetStatus?.used ? Number(budgetStatus.used) : 0;
  const remaining = budgetStatus?.remaining
    ? Number(budgetStatus.remaining)
    : budget - used;
  const percentage = budgetStatus?.percentage
    ? Number(budgetStatus.percentage)
    : budget > 0
      ? (used / budget) * 100
      : 0;

  // Get warning threshold from project settings (default to 85% if not configured)
  const warningThresholdPercent = projectBudgetSettings
    ? Number(projectBudgetSettings.warning_threshold_percent || 85)
    : 85;

  // Determine status color based on project warning threshold
  let statusColor = "#52c41a"; // green
  let statusText = "Healthy";

  if (percentage >= 100) {
    statusColor = "#ff4d4f"; // red
    statusText = "Exceeded";
  } else if (percentage >= warningThresholdPercent) {
    statusColor = "#faad14"; // orange
    statusText = "Warning";
  } else if (percentage >= warningThresholdPercent - 10) {
    statusColor = "#1890ff"; // blue
    statusText = "Monitoring";
  }

  const handleUpdate = (values: Record<string, unknown>) => {
    updateMutation.mutate({
      id: costElement.cost_element_id,
      data: {
        ...values,
        branch: costElement.branch || "main",
      },
    });
  };

  return (
    <div>
      {/* Budget Section */}
      <CollapsibleCard
        id="budget-status-card"
        title="Budget Status"
        style={{
          marginBottom: isMobile ? token.marginSM : token.marginMD,
        }}
        styles={{
          body: {
            padding: isMobile ? token.paddingSM : token.paddingLG,
          },
        }}
      >
        {isLoading ? (
          <Progress percent={0} />
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: token.paddingMD,
            }}
          >
            <Progress
              type="circle"
              percent={Math.round(Math.min(percentage, 100))}
              size={80}
              format={(percent) => `${percent}%`}
              strokeColor={statusColor}
            />
            <div>
              <Text strong style={{ fontSize: token.fontSizeLG }}>
                {statusText}
              </Text>
              <br />
              <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                Budget: €{budget.toFixed(2)} · Used: €{used.toFixed(2)} · Remaining: €{remaining.toFixed(2)}
              </Text>
              {remaining < 0 && (
                <>
                  <br />
                  <Text type="danger" style={{ fontSize: token.fontSizeSM }}>
                    ⚠ Over budget by €{Math.abs(remaining).toFixed(2)}
                  </Text>
                </>
              )}
              {percentage >= warningThresholdPercent && percentage < 100 && (
                <>
                  <br />
                  <Text type="warning" style={{ fontSize: token.fontSizeSM }}>
                    ⚠ Approaching budget limit (threshold: {warningThresholdPercent}%)
                  </Text>
                </>
              )}
            </div>
          </div>
        )}
      </CollapsibleCard>

      {/* Cost Element Details Section */}
      <CollapsibleCard
        id="cost-element-details-card"
        title="Cost Element Details"
        extra={
          <Button
            type="primary"
            size={isMobile ? "small" : "middle"}
            icon={<EditOutlined />}
            onClick={() => setIsEditModalOpen(true)}
          >
            {!isSmallMobile && "Update"}
          </Button>
        }
        styles={{
          body: {
            padding: isMobile ? token.paddingSM : token.paddingLG,
          },
        }}
      >
        <Descriptions
          bordered
          column={{ xs: 1, sm: 1, md: 2, lg: 2 }}
          size={isMobile ? "small" : "middle"}
          styles={{
            label: {
              width: isSmallMobile ? "100px" : "130px",
              fontSize: isSmallMobile ? token.fontSizeSM : token.fontSizeMD,
            },
            content: {
              fontSize: isSmallMobile ? token.fontSizeSM : token.fontSizeMD,
            },
          }}
        >
          <Descriptions.Item label="Code">{costElement.code}</Descriptions.Item>
          <Descriptions.Item label="Name">{costElement.name}</Descriptions.Item>
          <Descriptions.Item label="Description" span={isMobile ? 1 : screens.md ? 2 : 1}>
            {costElement.description || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Budget">
            €{Number(costElement.budget_amount).toLocaleString()}
          </Descriptions.Item>
          <Descriptions.Item label="Type">
            {costElement.cost_element_type_name || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="WBE">
            {costElement.wbe_name || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Branch">
            {costElement.branch || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Created By">
            {costElement.created_by || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Valid Time">
            {costElement.valid_time ? formatRangeDate(costElement.valid_time) : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Transaction Time">
            {costElement.transaction_time ? formatRangeDate(costElement.transaction_time) : "-"}
          </Descriptions.Item>
        </Descriptions>
      </CollapsibleCard>

      {/* EVM Time History Chart */}
      {/*
      <div style={{ marginBottom: 16 }}>
        <EVMTimeHistoryChart costElementId={costElement.cost_element_id} />
      </div>
      */}

      {/* EVM Forecast Comparison Section */}
      <ForecastComparisonCard
        costElementId={costElement.cost_element_id}
        budgetAmount={Number(costElement.budget_amount)}
      />

      <CostElementModal
        open={isEditModalOpen}
        onCancel={() => setIsEditModalOpen(false)}
        onOk={handleUpdate}
        confirmLoading={updateMutation.isPending}
        initialValues={costElement}
        currentBranch={costElement.branch || "main"}
        wbeId={costElement.wbe_id ?? undefined}
        wbeName={costElement.wbe_name ?? undefined}
      />
    </div>
  );
};
