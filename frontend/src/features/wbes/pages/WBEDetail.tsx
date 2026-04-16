/**
 * WBEDetail Page Component
 *
 * Displays detailed information about a Work Breakdown Element (WBE)
 * including EVM metrics and analysis capabilities.
 *
 * Features:
 * - Displays WBE basic information (name, code, description)
 * - Shows EVM summary with all key metrics
 * - Provides access to detailed EVM analysis via modal
 * - Integrates with TimeMachineContext for time-travel queries
 * - Proper loading and error states
 *
 * @module features/wbes/pages
 */

import { useState } from "react";
import { Spin, Alert, Descriptions, Typography, Card } from "antd";
import { useParams } from "react-router-dom";
import { EVMSummaryView } from "@/features/evm/components/EVMSummaryView";
import { EVMAnalyzerModal } from "@/features/evm/components/EVMAnalyzerModal";
import { useEVMMetrics, useEVMTimeSeries } from "@/features/evm/api/useEVMMetrics";
import { useWBE } from "../api/useWBEs";
import { EntityType } from "@/features/evm/types";
import type { EVMTimeSeriesGranularity } from "@/features/evm/types";
import { formatDate, formatTemporalRange } from "@/utils/formatters";

const { Title } = Typography;

/**
 * Props for WBEDetail component
 */
interface WBEDetailProps {
  /** WBE ID (from route params if not provided) */
  wbeId?: string;
}

/**
 * WBEDetail Component
 *
 * Renders a comprehensive detail view for a Work Breakdown Element,
 * including EVM metrics and analysis capabilities.
 */
export const WBEDetail: React.FC<WBEDetailProps> = ({ wbeId: propWbeId }) => {
  const { wbeId: paramWbeId } = useParams<{ wbeId?: string }>();
  const wbeId = propWbeId || paramWbeId;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>("week");

  // Fetch WBE data
  const { data: wbeData, isLoading: wbeLoading, error: wbeError } = useWBE(
    wbeId || ""
  );

  // Fetch EVM metrics for this WBE
  const { data: evmMetrics, isLoading: evmLoading } = useEVMMetrics(
    EntityType.WBE,
    wbeId || "",
    {
      enabled: !!wbeId,
    }
  );

  // Fetch time-series data for charts
  const { data: timeSeries, isLoading: timeSeriesLoading } = useEVMTimeSeries(
    EntityType.WBE,
    wbeId || "",
    granularity,
    {
      enabled: !!wbeId,
    }
  );

  /**
   * Render loading state
   */
  if (wbeLoading) {
    return (
      <div style={{ textAlign: "center", padding: "40px" }}>
        <Spin size="large" />
        <div style={{ marginTop: "16px" }}>Loading WBE details...</div>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (wbeError || !wbeData) {
    return (
      <Alert
        title="Error"
        description={wbeError instanceof Error ? wbeError.message : "Failed to load WBE"}
        type="error"
        showIcon
        style={{ margin: "24px" }}
      />
    );
  }

  /**
   * Handle granularity change
   */
  const handleGranularityChange = (newGranularity: EVMTimeSeriesGranularity) => {
    setGranularity(newGranularity);
  };

  /**
   * Handle opening the EVM Analyzer modal
   */
  const handleAdvancedClick = () => {
    setIsModalOpen(true);
  };

  /**
   * Handle closing the EVM Analyzer modal
   */
  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  return (
    <div style={{ padding: "24px" }}>
      {/* WBE Basic Information */}
      <Card style={{ marginBottom: "24px" }}>
        <Title level={2}>{wbeData.name}</Title>
        <Descriptions column={2} bordered>
          <Descriptions.Item label="Code">{wbeData.code}</Descriptions.Item>
          <Descriptions.Item label="Level">{wbeData.level}</Descriptions.Item>
          <Descriptions.Item label="Description" span={2}>
            {wbeData.description || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Project ID">{wbeData.project_id}</Descriptions.Item>
          <Descriptions.Item label="Parent ID">
            {wbeData.parent_id || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Created">
            {wbeData.transaction_time_formatted?.lower_formatted
              ? formatDate(wbeData.transaction_time_formatted.lower, { fallback: "-" })
              : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Valid Time">
            {wbeData.valid_time_formatted
              ? formatTemporalRange(wbeData.valid_time_formatted)
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
        <div style={{ textAlign: "center", padding: "40px" }}>
          <Spin size="large" />
          <div style={{ marginTop: "16px" }}>Loading EVM metrics...</div>
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
    </div>
  );
};

export default WBEDetail;
