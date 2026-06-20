/**
 * NotificationPreferencesPanel + TelegramConnectPanel
 *
 * Used on the Profile page. Renders the preference matrix grouped by category
 * with In-app/Telegram toggles, and a Telegram connect/disconnect flow that
 * polls status while a link is pending.
 */
import React, { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Space,
  Spin,
  Switch,
  Table,
  Tag,
  Typography,
} from "antd";
import type { ColumnType } from "antd/es/table";
import { LinkOutlined, CheckCircleOutlined } from "@ant-design/icons";
import {
  useNotificationPreferences,
  useUpdateNotificationPreferences,
  useConnectTelegram,
  useTelegramStatus,
  useDisconnectTelegram,
  type NotificationPreferenceEntry,
} from "../api/useNotificationPreferences";
import type { NotificationChannel } from "../api/useNotifications";

const { Title, Text, Paragraph } = Typography;

/** Telegram status polling interval while a connect is pending. */
const TELEGRAM_POLL_INTERVAL_MS = 3000;

interface PrefRow {
  key: string;
  eventType: string;
  inApp: NotificationPreferenceEntry | undefined;
  telegram: NotificationPreferenceEntry | undefined;
}

/**
 * Preference matrix grouped by category label. Each row is an event type with
 * In-app / Telegram switches; toggles fire an immediate (debounced by React's
 * event batching) PUT and invalidate the preferences query.
 */
export const NotificationPreferencesPanel: React.FC = () => {
  const { data, isLoading } = useNotificationPreferences();
  const updatePrefs = useUpdateNotificationPreferences();

  const handleToggle = (
    row: PrefRow,
    channel: NotificationChannel,
    enabled: boolean,
  ) => {
    updatePrefs.mutate([
      {
        event_type: row.eventType,
        channel,
        enabled,
      },
    ]);
  };

  const columns: ColumnType<PrefRow>[] = [
    {
      title: "Event",
      dataIndex: "eventType",
      key: "eventType",
      render: (et: string) => (
        <Text>{et.replace(/_/g, " ")}</Text>
      ),
    },
    {
      title: "In-app",
      key: "inApp",
      width: 90,
      align: "center" as const,
      render: (_, row) => (
        <Switch
          size="small"
          checked={row.inApp?.enabled ?? true}
          loading={updatePrefs.isPending}
          onChange={(checked) => handleToggle(row, "in_app", checked)}
        />
      ),
    },
    {
      title: "Telegram",
      key: "telegram",
      width: 100,
      align: "center" as const,
      render: (_, row) => (
        <Switch
          size="small"
          checked={row.telegram?.enabled ?? true}
          loading={updatePrefs.isPending}
          onChange={(checked) => handleToggle(row, "telegram", checked)}
        />
      ),
    },
  ];

  if (isLoading) {
    return (
      <Card title="Notification Preferences" variant="borderless">
        <div style={{ textAlign: "center", padding: 24 }}>
          <Spin />
        </div>
      </Card>
    );
  }

  return (
    <Card title="Notification Preferences" variant="borderless">
      {data?.categories?.length ? (
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          {data.categories.map((cat) => {
            // Group entries by event_type to align in_app + telegram columns.
            const byEventType = new Map<string, PrefRow>();
            for (const entry of cat.entries) {
              let row = byEventType.get(entry.event_type);
              if (!row) {
                row = {
                  key: entry.event_type,
                  eventType: entry.event_type,
                  inApp: undefined,
                  telegram: undefined,
                };
                byEventType.set(entry.event_type, row);
              }
              if (entry.channel === "in_app") row.inApp = entry;
              else if (entry.channel === "telegram") row.telegram = entry;
            }
            const rows = Array.from(byEventType.values());
            return (
              <div key={cat.category}>
                <Title level={5} style={{ marginTop: 0 }}>
                  {cat.label}
                </Title>
                <Table<PrefRow>
                  rowKey="key"
                  size="small"
                  columns={columns}
                  dataSource={rows}
                  pagination={false}
                  locale={{ emptyText: "No configurable events" }}
                />
              </div>
            );
          })}
        </Space>
      ) : (
        <Paragraph type="secondary">No notification preferences available.</Paragraph>
      )}
    </Card>
  );
};

/**
 * Telegram connection panel. Initiates a connect (which returns the bot +
 * authorize URL), polls status until verified, then offers Disconnect.
 */
export const TelegramConnectPanel: React.FC = () => {
  const [connectData, setConnectData] = useState<{
    bot_username: string;
    connect_url: string;
  } | null>(null);
  const [connectError, setConnectError] = useState<string | null>(null);

  const connect = useConnectTelegram({
    onSuccess: (data) => {
      setConnectData(data);
      setConnectError(null);
    },
    onError: (err) => {
      // 400 = Telegram not configured on the backend (or already linked).
      const msg = err.message || "";
      if (msg.includes("400")) {
        setConnectError(
          "Telegram is not configured on this server. Ask an administrator to set the Telegram bot token.",
        );
      } else {
        setConnectError(msg);
      }
    },
  });

  const disconnect = useDisconnectTelegram();

  // Poll status only while a connect is pending and not yet verified.
  // A pending connect is: we have issued a connect call AND the link is not
  // yet verified. We derive this from render state rather than an effect so
  // the refetchInterval stops automatically once verified.
  const status = useTelegramStatus({
    refetchInterval: connectData ? TELEGRAM_POLL_INTERVAL_MS : false,
  });

  const verified = status.data?.verified === true;
  const linked = status.data?.linked === true;
  // Pending connect state — null once the backend reports verified.
  const pendingConnect = connectData && !verified ? connectData : null;
  // Whether the server has Telegram configured/enabled (gates the Connect button).
  const telegramAvailable = status.data?.available === true;

  const handleConnect = () => {
    setConnectError(null);
    connect.mutate();
  };

  const handleDisconnect = () => {
    disconnect.mutate(undefined, {
      onSuccess: () => {
        setConnectData(null);
      },
    });
  };

  return (
    <Card title="Telegram" variant="borderless">
      {status.isLoading ? (
        <div style={{ textAlign: "center", padding: 24 }}>
          <Spin />
        </div>
      ) : verified && linked ? (
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="Status">
              <Tag color="success" icon={<CheckCircleOutlined />}>
                Connected
              </Tag>
            </Descriptions.Item>
            {status.data?.chat_id && (
              <Descriptions.Item label="Chat ID">
                {status.data.chat_id}
              </Descriptions.Item>
            )}
          </Descriptions>
          <Button danger onClick={handleDisconnect} loading={disconnect.isPending}>
            Disconnect
          </Button>
        </Space>
      ) : connectError ? (
        <Alert
          type="warning"
          showIcon
          message={connectError}
          action={
            <Button size="small" onClick={handleConnect} loading={connect.isPending}>
              Retry
            </Button>
          }
        />
      ) : pendingConnect ? (
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <Alert
            type="info"
            showIcon
            message={
              <span>
                Open this link to link your Telegram account with bot{" "}
                <Text code>@{pendingConnect.bot_username}</Text>:
              </span>
            }
            description={
              <a
                href={pendingConnect.connect_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Space>
                  <LinkOutlined />
                  {pendingConnect.connect_url}
                </Space>
              </a>
            }
          />
          <Space>
            <Spin size="small" />
            <Text type="secondary">Waiting for Telegram confirmation…</Text>
          </Space>
        </Space>
      ) : (
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <Paragraph type="secondary" style={{ margin: 0 }}>
            Connect a Telegram account to receive notifications outside the app.
          </Paragraph>
          <Button
            type="primary"
            onClick={handleConnect}
            loading={connect.isPending}
            disabled={!telegramAvailable}
          >
            Connect Telegram
          </Button>
          {!telegramAvailable && (
            <Alert
              type="info"
              showIcon
              message="Telegram is not configured on this server."
              description="An administrator must set the Telegram bot token and username before you can connect."
            />
          )}
        </Space>
      )}
    </Card>
  );
};
