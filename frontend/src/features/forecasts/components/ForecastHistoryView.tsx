import { useState } from "react";
import {
  Card,
  Timeline,
  Tag,
  Space,
  DatePicker,
  Select,
  Row,
  Col,
  Empty,
  Spin,
} from "antd";
import {
  HistoryOutlined,
  BranchesOutlined,
  CalendarOutlined,
} from "@ant-design/icons";
import type { Dayjs } from "dayjs";
import dayjs from "dayjs";
import isBetween from "dayjs/plugin/isBetween";
import relativeTime from "dayjs/plugin/relativeTime";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { useCostElement } from "@/features/cost-elements/api/useCostElements";
import { formatCurrency } from "@/utils/formatters";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";

dayjs.extend(isBetween);
dayjs.extend(relativeTime);

const { RangePicker } = DatePicker;

interface ForecastHistoryViewProps {
  costElementId: string;
  currentBranch?: string;
  projectId?: string;
}

export const ForecastHistoryView = ({
  costElementId,
  currentBranch = "main",
  projectId,
}: ForecastHistoryViewProps) => {
  const currency = useProjectCurrency(projectId);
  const { asOf } = useTimeMachineParams();
  const [selectedBranch, setSelectedBranch] = useState<string>(currentBranch);
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);

  // Fetch current cost element data
  const { data: costElement, isLoading } = useCostElement(
    costElementId,
    selectedBranch,
  );

  if (isLoading) {
    return (
      <Card title={<Space><HistoryOutlined /><span>Forecast History</span></Space>}>
        <div style={{ textAlign: "center", padding: 24 }}>
          <Spin />
        </div>
      </Card>
    );
  }

  if (!costElement) {
    return (
      <Card title={<Space><HistoryOutlined /><span>Forecast History</span></Space>}>
        <Empty
          description="No cost element data found"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    );
  }

  // Build a simple timeline from the current version data
  const createdDate = costElement.valid_time_formatted?.lower
    ? dayjs(costElement.valid_time_formatted.lower as string)
    : null;

  return (
    <Card
      title={
        <Space>
          <HistoryOutlined />
          <span>Forecast History</span>
        </Space>
      }
      extra={
        <Space>
          {asOf && (
            <Tag color="orange">
              Viewing as of: {dayjs(asOf).format("YYYY-MM-DD")}
            </Tag>
          )}
        </Space>
      }
    >
      {/* Filters */}
      <Card
        type="inner"
        title="Filters"
        style={{ marginBottom: 16 }}
        size="small"
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12}>
            <div style={{ marginBottom: 8 }}>
              <BranchesOutlined style={{ marginRight: 8 }} />
              <span>Branch:</span>
            </div>
            <Select
              value={selectedBranch}
              onChange={setSelectedBranch}
              style={{ width: "100%" }}
              options={[
                { label: "Main", value: "main" },
                { label: "Feature Branch", value: "feature" },
              ]}
            />
          </Col>
          <Col xs={24} sm={12}>
            <div style={{ marginBottom: 8 }}>
              <CalendarOutlined style={{ marginRight: 8 }} />
              <span>Date Range:</span>
            </div>
            <RangePicker
              value={dateRange}
              onChange={(dates) => setDateRange(dates as [Dayjs, Dayjs] | null)}
              style={{ width: "100%" }}
            />
          </Col>
        </Row>
      </Card>

      {/* Current Version */}
      <Card
        type="inner"
        title={
          <Space>
            <span>Current Version</span>
            <Tag color="blue">1 version</Tag>
          </Space>
        }
      >
        <Timeline
          mode="left"
          items={[
            {
              color: "green",
              label: (
                <div style={{ fontSize: "12px" }}>
                  <div style={{ fontWeight: "bold" }}>
                    {createdDate ? createdDate.format("YYYY-MM-DD HH:mm") : "Current"}
                  </div>
                </div>
              ),
              children: (
                <Card
                  size="small"
                  style={{
                    marginBottom: 8,
                    borderLeft: "3px solid #52c41a",
                  }}
                >
                  <Row gutter={[16, 8]}>
                    <Col span={8}>
                      <div style={{ fontSize: "12px", color: "#999" }}>
                        Amount
                      </div>
                      <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                        {formatCurrency(costElement.amount, currency)}
                      </div>
                    </Col>
                    <Col span={8}>
                      <div style={{ fontSize: "12px", color: "#999" }}>
                        Type
                      </div>
                      <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                        {costElement.cost_element_type_name || "-"}
                      </div>
                    </Col>
                    <Col span={8}>
                      <div style={{ fontSize: "12px", color: "#999" }}>
                        Work Package
                      </div>
                      <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                        {costElement.work_package_name || "-"}
                      </div>
                    </Col>
                  </Row>
                </Card>
              ),
            },
          ]}
        />
      </Card>
    </Card>
  );
};
