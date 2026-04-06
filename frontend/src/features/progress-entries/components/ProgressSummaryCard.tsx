import { Card, Progress, Alert, Typography, List, Space, theme } from "antd";
import type { ProgressEntryRead } from "@/api/generated";
import dayjs from "dayjs";

const { Text } = Typography;

interface ProgressSummaryCardProps {
  /** Latest progress entry to display */
  latestEntry: ProgressEntryRead | null | undefined;
  /** Optional historical entries (shown below the main summary) */
  historyEntries?: ProgressEntryRead[];
  /** When true, render content only without the surrounding Card */
  hideCard?: boolean;
}

/**
 * Format a TSTZRANGE valid_time to a readable date string.
 * Example input: '["2026-01-31T00:00:00Z",)'
 */
const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return "-";
  // Extract lower bound from TSTZRANGE format
  const lowerBound = dateStr.split(",")[0].substring(1).replace(/"/g, "");
  return dayjs(lowerBound).format("MMM D, YYYY");
};

/**
 * ProgressSummaryCard Component
 *
 * Displays the latest progress entry with a circular progress indicator,
 * along with optional historical entries in a compact list format.
 *
 * Used by both the ProgressTrackerWidget and ProgressEntriesTab.
 */
export const ProgressSummaryCard: React.FC<ProgressSummaryCardProps> = ({
  latestEntry,
  historyEntries = [],
  hideCard = false,
}) => {
  const { token } = theme.useToken();

  const progressPercent = latestEntry
    ? Math.round(parseFloat(latestEntry.progress_percentage))
    : 0;

  const summaryContent = (
    <Space direction="vertical" style={{ width: "100%" }} size={token.paddingMD}>
      {latestEntry ? (
        <>
          {/* Main progress summary with circle */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: token.paddingMD,
            }}
          >
            <Progress
              type="circle"
              percent={progressPercent}
              size={80}
              format={(percent) => `${percent}%`}
              strokeColor={token.colorPrimary}
            />
            <div style={{ flex: 1 }}>
              <Text strong style={{ fontSize: token.fontSizeLG }}>
                {progressPercent}% Complete
              </Text>
              <br />
              <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                As of {formatDate(latestEntry.valid_time)}
              </Text>
              {latestEntry.notes && (
                <>
                  <br />
                  <Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeXS }}
                  >
                    {latestEntry.notes}
                  </Text>
                </>
              )}
            </div>
          </div>

          {/* Historical entries list */}
          {historyEntries.length > 0 && (
            <List
              size="small"
              dataSource={historyEntries}
              renderItem={(entry) => {
                const pct = Math.round(parseFloat(entry.progress_percentage));
                return (
                  <List.Item style={{ padding: `${token.paddingXS}px 0` }}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        width: "100%",
                      }}
                    >
                      <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                        {formatDate(entry.valid_time)}
                      </Text>
                      <Text style={{ fontSize: token.fontSizeSM }}>{pct}%</Text>
                    </div>
                  </List.Item>
                );
              }}
            />
          )}
        </>
      ) : (
        <Alert
          message="No progress entries found"
          type="info"
          showIcon
          style={{ marginTop: token.paddingSM }}
        />
      )}
    </Space>
  );

  if (hideCard) return summaryContent;

  return (
    <Card>
      <Space direction="vertical" style={{ width: "100%" }}>
        {summaryContent}
      </Space>
    </Card>
  );
};
