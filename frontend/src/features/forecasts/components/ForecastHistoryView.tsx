import { useState } from "react";
import {
  Card,
  Timeline,
  Tag,
  Button,
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
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { useForecasts } from "../api";

const { RangePicker } = DatePicker;

interface ForecastHistoryViewProps {
  costElementId: string;
  currentBranch?: string;
}

export const ForecastHistoryView = ({
  costElementId,
  currentBranch = "main",
}: ForecastHistoryViewProps) => {
  const { asOf, setAsOf } = useTimeMachineParams();
  const [selectedBranch, setSelectedBranch] = useState<string>(currentBranch);
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);

  // Fetch all forecasts for this cost element across time
  // Using pagination to get historical versions
  const { data: forecastsData, isLoading } = useForecasts({
    cost_element_id: costElementId,
    branch: selectedBranch,
    pagination: { current: 1, pageSize: 100 }, // Get all versions
  });

  const forecasts = forecastsData?.items || [];

  // Filter by date range if specified
  const filteredForecasts = forecasts.filter((forecast) => {
    if (!dateRange) return true;
    const forecastDate = dayjs(forecast.created_at);
    return forecastDate.isBetween(dateRange[0], dateRange[1], "day", "[]");
  });

  // Sort by creation date (newest first)
  const sortedForecasts = [...filteredForecasts].sort(
    (a, b) => dayjs(b.created_at).unix() - dayjs(a.created_at).unix(),
  );

  // Calculate variance from budget for color coding
  const getVarianceColor = (eac: string, budget: number) => {
    const vac = budget - Number(eac);
    if (vac < 0) return "red";
    if (vac > 0) return "green";
    return "blue";
  };

  const getVarianceText = (eac: string, budget: number) => {
    const vac = budget - Number(eac);
    if (vac < 0) return "Over Budget";
    if (vac > 0) return "Under Budget";
    return "On Budget";
  };

  const handleAsOfChange = (date: Dayjs | null) => {
    if (date) {
      setAsOf(date.toISOString());
    } else {
      setAsOf(undefined);
    }
  };

  const handleTimeTravel = (forecastDate: string) => {
    setAsOf(dayjs(forecastDate).toISOString());
  };

  const resetTimeMachine = () => {
    setAsOf(undefined);
  };

  return (
    <Card
      title={
        <Space>
          <HistoryOutlined />
          <span>Forecast History & Time Travel</span>
        </Space>
      }
      extra={
        <Space>
          {asOf && (
            <Tag color="orange" closable onClose={resetTimeMachine}>
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
          <Col xs={24} sm={8}>
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
          <Col xs={24} sm={8}>
            <div style={{ marginBottom: 8 }}>
              <CalendarOutlined style={{ marginRight: 8 }} />
              <span>Time Travel (As Of):</span>
            </div>
            <DatePicker
              value={asOf ? dayjs(asOf) : null}
              onChange={handleAsOfChange}
              style={{ width: "100%" }}
              allowClear
              placeholder="Select point in time"
            />
          </Col>
          <Col xs={24} sm={8}>
            <div style={{ marginBottom: 8 }}>
              <span>Date Range:</span>
            </div>
            <RangePicker
              value={dateRange}
              onChange={setDateRange}
              style={{ width: "100%" }}
            />
          </Col>
        </Row>
      </Card>

      {/* History Timeline */}
      <Card
        type="inner"
        title={
          <Space>
            <span>Version History</span>
            <Tag color="blue">{sortedForecasts.length} versions</Tag>
          </Space>
        }
      >
        {isLoading ? (
          <div style={{ textAlign: "center", padding: 24 }}>
            <Spin />
          </div>
        ) : sortedForecasts.length === 0 ? (
          <Empty
            description="No forecast history found for this cost element"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <Timeline
            mode="left"
            items={sortedForecasts.map((forecast, index) => {
              const createdDate = dayjs(forecast.created_at);
              const isLatest = index === 0;
              const isCurrentView = asOf
                ? createdDate.isBefore(dayjs(asOf))
                : isLatest;

              return {
                color: isLatest ? "green" : "blue",
                label: (
                  <div style={{ fontSize: "12px" }}>
                    <div style={{ fontWeight: "bold" }}>
                      {createdDate.format("YYYY-MM-DD HH:mm")}
                    </div>
                    <div style={{ color: "#999" }}>{createdDate.fromNow()}</div>
                  </div>
                ),
                children: (
                  <Card
                    size="small"
                    style={{
                      marginBottom: 8,
                      borderLeft: `3px solid ${
                        isLatest ? "#52c41a" : "#1890ff"
                      }`,
                    }}
                    extra={
                      <Space>
                        <Tag
                          color={forecast.branch === "main" ? "blue" : "orange"}
                        >
                          {forecast.branch}
                        </Tag>
                        {!isCurrentView && (
                          <Button
                            type="link"
                            size="small"
                            onClick={() =>
                              handleTimeTravel(forecast.created_at)
                            }
                          >
                            View as of this date
                          </Button>
                        )}
                      </Space>
                    }
                  >
                    <Row gutter={[16, 8]}>
                      <Col span={8}>
                        <div style={{ fontSize: "12px", color: "#999" }}>
                          EAC (Estimate at Complete)
                        </div>
                        <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                          €{Number(forecast.eac_amount).toLocaleString()}
                        </div>
                      </Col>
                      <Col span={8}>
                        <div style={{ fontSize: "12px", color: "#999" }}>
                          Status
                        </div>
                        <Tag color={getVarianceColor(forecast.eac_amount, 0)}>
                          {getVarianceText(forecast.eac_amount, 0)}
                        </Tag>
                      </Col>
                      <Col span={8}>
                        <div style={{ fontSize: "12px", color: "#999" }}>
                          Created by
                        </div>
                        <div>{forecast.created_by}</div>
                      </Col>
                      <Col span={24}>
                        <div style={{ fontSize: "12px", color: "#999" }}>
                          Basis of Estimate
                        </div>
                        <div style={{ fontSize: "13px" }}>
                          {forecast.basis_of_estimate}
                        </div>
                      </Col>
                      {forecast.valid_time && (
                        <Col span={24}>
                          <div style={{ fontSize: "11px", color: "#999" }}>
                            Valid Time:{" "}
                            {dayjs(forecast.valid_time).format("YYYY-MM-DD")}
                          </div>
                        </Col>
                      )}
                      {forecast.transaction_time && (
                        <Col span={24}>
                          <div style={{ fontSize: "11px", color: "#999" }}>
                            Transaction Time:{" "}
                            {dayjs(forecast.transaction_time).format(
                              "YYYY-MM-DD HH:mm:ss",
                            )}
                          </div>
                        </Col>
                      )}
                    </Row>
                  </Card>
                ),
              };
            })}
          />
        )}
      </Card>

      {/* Statistics */}
      {sortedForecasts.length > 0 && (
        <Card type="inner" title="Statistics" style={{ marginTop: 16 }}>
          <Row gutter={[16, 16]}>
            <Col span={8}>
              <div style={{ textAlign: "center" }}>
                <div
                  style={{
                    fontSize: "24px",
                    fontWeight: "bold",
                    color: "#1890ff",
                  }}
                >
                  {sortedForecasts.length}
                </div>
                <div style={{ fontSize: "12px", color: "#999" }}>
                  Total Versions
                </div>
              </div>
            </Col>
            <Col span={8}>
              <div style={{ textAlign: "center" }}>
                <div
                  style={{
                    fontSize: "24px",
                    fontWeight: "bold",
                    color: "#52c41a",
                  }}
                >
                  {sortedForecasts[0]?.eac_amount || "N/A"}
                </div>
                <div style={{ fontSize: "12px", color: "#999" }}>
                  Latest EAC
                </div>
              </div>
            </Col>
            <Col span={8}>
              <div style={{ textAlign: "center" }}>
                <div
                  style={{
                    fontSize: "24px",
                    fontWeight: "bold",
                    color: "#fa8c16",
                  }}
                >
                  {sortedForecasts.length > 1
                    ? (
                        ((Number(sortedForecasts[0]?.eac_amount) -
                          Number(
                            sortedForecasts[sortedForecasts.length - 1]
                              ?.eac_amount,
                          )) /
                          Number(
                            sortedForecasts[sortedForecasts.length - 1]
                              ?.eac_amount,
                          )) *
                        100
                      ).toFixed(1)
                    : 0}
                  %
                </div>
                <div style={{ fontSize: "12px", color: "#999" }}>
                  EAC Change Over Time
                </div>
              </div>
            </Col>
          </Row>
        </Card>
      )}
    </Card>
  );
};
