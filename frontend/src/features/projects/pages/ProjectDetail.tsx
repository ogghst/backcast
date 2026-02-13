/**
 * ProjectDetail Page Component
 *
 * Displays detailed information about a Project
 * including EVM metrics and analysis capabilities.
 *
 * Features:
 * - Displays Project basic information (name, code, description, dates, customer)
 * - Shows EVM summary with all key metrics
 * - Provides access to detailed EVM analysis via modal
 * - Integrates with TimeMachineContext for time-travel queries
 * - Proper loading and error states
 *
 * @module features/projects/pages
 */

import { useState } from "react";
import { Spin, Alert, Descriptions, Typography, Card } from "antd";
import { useParams } from "react-router-dom";
import { EVMSummaryView } from "@/features/evm/components/EVMSummaryView";
import { EVMAnalyzerModal } from "@/features/evm/components/EVMAnalyzerModal";
import { useEVMMetrics, useEVMTimeSeries } from "@/features/evm/api/useEVMMetrics";
import { useProject } from "../api/useProjects";
import { EntityType } from "@/features/evm/types";
import type { EVMTimeSeriesGranularity } from "@/features/evm/types";

const { Title } = Typography;

/**
 * Props for ProjectDetail component
 */
interface ProjectDetailProps {
  /** Project ID (from route params if not provided) */
  projectId?: string;
}

/**
 * ProjectDetail Component
 *
 * Renders a comprehensive detail view for a Project,
 * including EVM metrics and analysis capabilities.
 */
export const ProjectDetail: React.FC<ProjectDetailProps> = ({ projectId: propProjectId }) => {
  const { projectId: paramProjectId } = useParams<{ projectId?: string }>();
  const projectId = propProjectId || paramProjectId;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>("week");

  // Fetch Project data
  const { data: projectData, isLoading: projectLoading, error: projectError } = useProject(
    projectId || ""
  );

  // Fetch EVM metrics for this Project
  const { data: evmMetrics, isLoading: evmLoading } = useEVMMetrics(
    EntityType.PROJECT,
    projectId || "",
    {
      enabled: !!projectId,
    }
  );

  // Fetch time-series data for charts
  const { data: timeSeries, isLoading: timeSeriesLoading } = useEVMTimeSeries(
    EntityType.PROJECT,
    projectId || "",
    granularity,
    {
      enabled: !!projectId,
    }
  );

  /**
   * Render loading state
   */
  if (projectLoading) {
    return (
      <div style={{ textAlign: "center", padding: "40px" }}>
        <Spin size="large" />
        <div style={{ marginTop: "16px" }}>Loading Project details...</div>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (projectError || !projectData) {
    return (
      <Alert
        title="Error"
        description={projectError instanceof Error ? projectError.message : "Failed to load Project"}
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
      {/* Project Basic Information */}
      <Card style={{ marginBottom: "24px" }}>
        <Title level={2}>{projectData.name}</Title>
        <Descriptions column={2} bordered>
          <Descriptions.Item label="Code">{projectData.code}</Descriptions.Item>
          <Descriptions.Item label="Customer">{projectData.customer || "-"}</Descriptions.Item>
          <Descriptions.Item label="Start Date">{projectData.start_date || "-"}</Descriptions.Item>
          <Descriptions.Item label="Target End Date">
            {projectData.target_end_date || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Description" span={2}>
            {projectData.description || "-"}
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

export default ProjectDetail;
