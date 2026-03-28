import { useState } from "react";
import {
  Descriptions,
  Progress,
  Statistic,
  Row,
  Col,
  Alert,
  Button,
  Grid,
  theme,
} from "antd";
import { EditOutlined } from "@ant-design/icons";
import type { CostElementRead } from "@/api/generated";
import { useBudgetStatus } from "@/features/cost-registration/api/useCostRegistrations";
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

interface OverviewTabProps {
  costElement: CostElementRead;
}

const { useBreakpoint } = Grid;

export const OverviewTab = ({ costElement }: OverviewTabProps) => {
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

  // Determine status color
  let statusColor = "#52c41a"; // green
  let statusText = "Healthy";

  if (percentage >= 100) {
    statusColor = "#ff4d4f"; // red
    statusText = "Exceeded";
  } else if (percentage >= 90) {
    statusColor = "#faad14"; // orange
    statusText = "Warning";
  } else if (percentage >= 75) {
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
          <>
            <Row
              gutter={[isMobile ? token.marginSM : token.marginLG, isMobile ? token.marginSM : token.marginMD]}
              style={{ marginBottom: isMobile ? token.marginMD : token.marginLG }}
            >
              <Col xs={12} sm={12} md={6}>
                <Statistic
                  title="Budget"
                  value={budget}
                  precision={2}
                  prefix="€"
                  styles={{
                    content: {
                      color: token.colorInfo,
                      fontSize: isSmallMobile ? token.fontSizeLG : token.fontSizeXL,
                    },
                    title: {
                      fontSize: isSmallMobile ? token.fontSizeSM : token.fontSizeMD,
                    },
                  }}
                />
              </Col>
              <Col xs={12} sm={12} md={6}>
                <Statistic
                  title="Used"
                  value={used}
                  precision={2}
                  prefix="€"
                  styles={{
                    content: {
                      color: percentage >= 100 ? token.colorError : token.colorSuccess,
                      fontSize: isSmallMobile ? token.fontSizeLG : token.fontSizeXL,
                    },
                    title: {
                      fontSize: isSmallMobile ? token.fontSizeSM : token.fontSizeMD,
                    },
                  }}
                />
              </Col>
              <Col xs={12} sm={12} md={6}>
                <Statistic
                  title="Remaining"
                  value={remaining}
                  precision={2}
                  prefix="€"
                  styles={{
                    content: {
                      color: remaining < 0 ? token.colorError : token.colorSuccess,
                      fontSize: isSmallMobile ? token.fontSizeLG : token.fontSizeXL,
                    },
                    title: {
                      fontSize: isSmallMobile ? token.fontSizeSM : token.fontSizeMD,
                    },
                  }}
                />
              </Col>
              <Col xs={12} sm={12} md={6}>
                <Statistic
                  title="Used"
                  value={percentage}
                  precision={1}
                  suffix="%"
                  styles={{
                    content: {
                      color: statusColor,
                      fontSize: isSmallMobile ? token.fontSizeLG : token.fontSizeXL,
                    },
                    title: {
                      fontSize: isSmallMobile ? token.fontSizeSM : token.fontSizeMD,
                    },
                  }}
                />
              </Col>
            </Row>

            <Progress
              percent={Math.min(percentage, 100)}
              strokeColor={statusColor}
              status={percentage >= 100 ? "exception" : undefined}
              strokeHeight={isMobile ? 8 : 10}
            />
            <div style={{
              marginTop: token.paddingXS,
              color: token.colorTextSecondary,
              fontSize: isSmallMobile ? token.fontSizeSM : token.fontSizeMD,
            }}>
              Status:{" "}
              <strong style={{ color: statusColor }}>{statusText}</strong>
            </div>

            {remaining < 0 && (
              <Alert
                message="Budget Exceeded"
                description={isSmallMobile
                  ? `Over budget by €${Math.abs(remaining).toFixed(2)}`
                  : `This cost element has exceeded its budget by €${Math.abs(remaining).toFixed(2)}.`
                }
                type="warning"
                showIcon
                style={{
                  marginTop: isMobile ? token.marginSM : token.marginMD,
                  fontSize: isSmallMobile ? token.fontSizeSM : token.fontSizeMD,
                }}
              />
            )}

            {percentage >= 90 && percentage < 100 && (
              <Alert
                message="Budget Warning"
                description={isSmallMobile
                  ? `Used ${percentage.toFixed(1)}% of budget`
                  : `This cost element has used ${percentage.toFixed(1)}% of its budget. Consider reviewing before adding more costs.`
                }
                type="warning"
                showIcon
                style={{
                  marginTop: isMobile ? token.marginSM : token.marginMD,
                  fontSize: isSmallMobile ? token.fontSizeSM : token.fontSizeMD,
                }}
              />
            )}
          </>
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
            {costElement.valid_time
              ? new Date(costElement.valid_time).toLocaleString()
              : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Transaction Time">
            {costElement.transaction_time ?? "-"}
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
