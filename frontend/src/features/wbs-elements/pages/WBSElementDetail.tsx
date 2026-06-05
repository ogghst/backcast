/**
 * WBSElementDetail Page Component
 *
 * Displays detailed information about a WBS Element
 * including EVM metrics and analysis capabilities.
 */

import { useState } from "react";
import { Spin, Alert, Descriptions, Typography, Card, theme } from "antd";
import { useParams } from "react-router-dom";
import { EVMSummaryView } from "@/features/evm/components/EVMSummaryView";
import { EVMAnalyzerModal } from "@/features/evm/components/EVMAnalyzerModal";
import { useEVMMetrics, useEVMTimeSeries } from "@/features/evm/api/useEVMMetrics";
import { useWBSElement } from "../api/useWBSElements";
import { EntityType } from "@/features/evm/types";
import { EVMTimeSeriesGranularity } from "@/features/evm/types";
import { formatDate, formatTemporalRange } from "@/utils/formatters";
import { PageWrapper } from "@/components/layout";

const { Title } = Typography;

/**
 * Props for WBSElementDetail component
 */
export interface WBSElementDetailProps {
  /** WBS Element ID (from route params if not provided) */
  wbsElementId?: string;
}

/**
 * WBSElementDetail Component
 *
 * Renders a comprehensive detail view for a WBS Element,
 * including EVM metrics and analysis capabilities.
 */
export const WBSElementDetail: React.FC<WBSElementDetailProps> = ({ wbsElementId: propId }) => {
  const { wbsElementId: paramId } = useParams<{ wbsElementId?: string }>();
  const wbsElementId = propId || paramId;
  const { token } = theme.useToken();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>(EVMTimeSeriesGranularity.WEEK);

  // Fetch WBS Element data
  const { data: wbsData, isLoading: wbsLoading, error: wbsError } = useWBSElement(
    wbsElementId || ""
  );

  // Fetch EVM metrics for this WBS Element
  const { data: evmMetrics, isLoading: evmLoading } = useEVMMetrics(
    EntityType.WBS_ELEMENT,
    wbsElementId || "",
  );

  // Fetch time-series data for charts
  const { data: timeSeries, isLoading: timeSeriesLoading } = useEVMTimeSeries(
    EntityType.WBS_ELEMENT,
    wbsElementId || "",
    granularity,
  );

  if (wbsLoading) {
    return (
      <div style={{ textAlign: "center", padding: token.paddingXL }}>
        <Spin size="large" />
        <div style={{ marginTop: token.paddingMD }}>Loading WBS Element details...</div>
      </div>
    );
  }

  if (wbsError || !wbsData) {
    return (
      <Alert
        title="Error"
        description={wbsError instanceof Error ? wbsError.message : "Failed to load WBS Element"}
        type="error"
        showIcon
        style={{ margin: token.paddingLG }}
      />
    );
  }

  const handleGranularityChange = (newGranularity: EVMTimeSeriesGranularity) => {
    setGranularity(newGranularity);
  };

  const handleAdvancedClick = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  return (
    <PageWrapper>
      {/* WBS Element Basic Information */}
      <Card style={{ marginBottom: token.marginLG }}>
        <Title level={2}>{wbsData.name}</Title>
        <Descriptions column={2} bordered>
          <Descriptions.Item label="Code">{wbsData.code}</Descriptions.Item>
          <Descriptions.Item label="Level">{wbsData.level}</Descriptions.Item>
          <Descriptions.Item label="Description" span={2}>
            {wbsData.description || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Project ID">{wbsData.project_id}</Descriptions.Item>
          <Descriptions.Item label="Parent ID">
            {wbsData.parent_wbs_element_id || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Created">
            {wbsData.transaction_time_formatted?.lower_formatted
              ? formatDate(wbsData.transaction_time_formatted.lower as string | null | undefined, { fallback: "-" })
              : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Valid Time">
            {wbsData.valid_time_formatted
              ? formatTemporalRange(wbsData.valid_time_formatted as Record<string, string | null>)
              : "-"}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* EVM Summary Section */}
      {evmMetrics && !evmLoading ? (
        <EVMSummaryView
          metrics={evmMetrics}
          onAdvanced={handleAdvancedClick}
        />
      ) : evmLoading ? (
        <div style={{ textAlign: "center", padding: token.paddingXL }}>
          <Spin size="large" />
          <div style={{ marginTop: token.paddingMD }}>Loading EVM metrics...</div>
        </div>
      ) : null}

      {/* EVM Analyzer Modal */}
      <EVMAnalyzerModal
        open={isModalOpen}
        onClose={handleCloseModal}
        evmMetrics={evmMetrics}
        timeSeries={timeSeries}
        loading={evmLoading || timeSeriesLoading}
        onGranularityChange={handleGranularityChange}
      />
    </PageWrapper>
  );
};

export default WBSElementDetail;
