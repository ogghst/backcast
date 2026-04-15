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
import { useCostElementHistory } from "@/features/cost-elements/api/useCostElements";
import { parseRangeLowerBound, formatRangeDate } from "@/utils/temporal";

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

  // Fetch cost element history (includes forecast data due to 1:1 relationship)
  const { data: historyData, isLoading } = useCostElementHistory(
    costElementId,
    selectedBranch,
  );

  const costElementHistory = historyData || [];

  // Filter by date range if specified
  const filteredHistory = costElementHistory.filter((ce) => {
    if (!dateRange) return true;
    const ceDate = dayjs(parseRangeLowerBound(ce.transaction_time) || ce.created_at);
    return ceDate.isBetween(dateRange[0], dateRange[1], "day", "[]");
  });

  // Sort by transaction time (newest first)
  const sortedHistory = [...filteredHistory].sort(
    (a, b) => {
      const aTime = parseRangeLowerBound(a.transaction_time) || new Date(a.created_at);
      const bTime = parseRangeLowerBound(b.transaction_time) || new Date(b.created_at);
      return bTime.getTime() - aTime.getTime();
    },
  );

  // Get forecast from cost element data
  const getForecastFromCostElement = (ce: typeof costElementHistory[0]) => {
    return ce.forecast;
  };

  // Calculate variance from budget for color coding
  const getVarianceColor = (eac: number | null, budget: number) => {
    if (eac === null) return "default";
    const vac = budget - eac;
    if (vac < 0) return "red";
    if (vac > 0) return "green";
    return "blue";
  };

  const getVarianceText = (eac: number | null, budget: number) => {
    if (eac === null) return "No Forecast";
    const vac = budget - eac;
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

  const handleTimeTravel = (transactionTime: string | null | undefined) => {
    const date = parseRangeLowerBound(transactionTime);
    if (date) {
      setAsOf(date.toISOString());
    }
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
            <Tag color="blue">{sortedHistory.length} versions</Tag>
          </Space>
        }
      >
        {isLoading ? (
          <div style={{ textAlign: "center", padding: 24 }}>
            <Spin />
          </div>
        ) : sortedHistory.length === 0 ? (
          <Empty
            description="No history found for this cost element"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <Timeline
            mode="left"
            items={sortedHistory.map((ce, index) => {
              const forecast = getForecastFromCostElement(ce);
              const createdDate = dayjs(parseRangeLowerBound(ce.transaction_time) || ce.created_at);
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
                        <Tag color={ce.branch === "main" ? "blue" : "orange"}>
                          {ce.branch}
                        </Tag>
                        {!isCurrentView && (
                          <Button
                            type="link"
                            size="small"
                            onClick={() => handleTimeTravel(ce.transaction_time)}
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
                          Budget (BAC)
                        </div>
                        <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                          €{Number(ce.budget_amount).toLocaleString()}
                        </div>
                      </Col>
                      <Col span={8}>
                        <div style={{ fontSize: "12px", color: "#999" }}>
                          EAC (Estimate at Complete)
                        </div>
                        <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                          {forecast?.eac_amount
                            ? `€${Number(forecast.eac_amount).toLocaleString()}`
                            : "No forecast"}
                        </div>
                      </Col>
                      <Col span={8}>
                        <div style={{ fontSize: "12px", color: "#999" }}>
                          Status
                        </div>
                        <Tag color={getVarianceColor(forecast?.eac_amount ?? null, Number(ce.budget_amount))}>
                          {getVarianceText(forecast?.eac_amount ?? null, Number(ce.budget_amount))}
                        </Tag>
                      </Col>
                      <Col span={24}>
                        <div style={{ fontSize: "12px", color: "#999" }}>
                          Basis of Estimate
                        </div>
                        <div style={{ fontSize: "13px" }}>
                          {forecast?.basis_of_estimate || "No forecast data"}
                        </div>
                      </Col>
                      {ce.valid_time && (
                        <Col span={24}>
                          <div style={{ fontSize: "11px", color: "#999" }}>
                            Valid: {formatRangeDate(ce.valid_time, "short")} → {formatRangeDate(ce.valid_time)}
                          </div>
                        </Col>
                      )}
                      {ce.transaction_time && (
                        <Col span={24}>
                          <div style={{ fontSize: "11px", color: "#999" }}>
                            Recorded: {formatRangeDate(ce.transaction_time, "short")}
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
      {sortedHistory.length > 0 && (
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
                  {sortedHistory.length}
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
                  {sortedHistory[0]?.forecast?.eac_amount
                    ? `€${Number(sortedHistory[0].forecast.eac_amount).toLocaleString()}`
                    : "N/A"}
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
                  {sortedHistory.length > 1 && sortedHistory[0]?.forecast?.eac_amount && sortedHistory[sortedHistory.length - 1]?.forecast?.eac_amount
                    ? (
                        ((Number(sortedHistory[0].forecast.eac_amount) -
                          Number(sortedHistory[sortedHistory.length - 1].forecast?.eac_amount)) /
                          Number(sortedHistory[sortedHistory.length - 1].forecast?.eac_amount)) *
                        100
                      ).toFixed(1)
                    : sortedHistory.length > 1 && sortedHistory[0]?.forecast?.eac_amount
                      ? ((Number(sortedHistory[0].forecast.eac_amount) - Number(sortedHistory[0].budget_amount)) / Number(sortedHistory[0].budget_amount) * 100).toFixed(1)
                      : "0"}
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
