import { useState } from "react";
import { Card, Button, theme, Grid } from "antd";
import { DownOutlined, UpOutlined } from "@ant-design/icons";

interface CollapsibleCardProps {
  title: React.ReactNode;
  id: string;
  children: React.ReactNode;
  /** Whether the card is initially collapsed */
  collapsed?: boolean;
  /** Extra content to display in the header */
  extra?: React.ReactNode;
  /** Style for the card */
  style?: React.CSSProperties;
  /**
   * When true, children stay mounted while collapsed (hidden via `display: none`)
   * instead of being unmounted. Use this when children must remain registered
   * while hidden (e.g. Antd Form.Item fields inside a collapsed card).
   * Defaults to false to preserve the original unmount-on-collapse behavior
   * (avoiding zero-size resize bugs for mounted-while-hidden charts).
   */
  keepMounted?: boolean;
}

/**
 * CollapsibleCard - A Card component with collapsible content.
 *
 * The header is clickable to toggle the visibility of the content.
 * Shows an up/down arrow icon to indicate the current state.
 */
export function CollapsibleCard({
  title,
  id,
  children,
  collapsed: defaultCollapsed = false,
  extra,
  style,
  keepMounted = false,
}: CollapsibleCardProps): JSX.Element {
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  const toggleCollapse = () => {
    setCollapsed(!collapsed);
  };

  return (
    <Card
      id={id}
      style={style}
      styles={{
        body: {
          padding: token.paddingXS,
        },
      }}
      title={
        <div
          onClick={toggleCollapse}
          style={{
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            width: "100%",
            gap: isMobile ? token.marginXS : token.marginSM,
          }}
        >
          <span style={{ flex: 1, minWidth: 0 }}>{title}</span>
          <Button
            type="text"
            size="small"
            icon={collapsed ? <DownOutlined /> : <UpOutlined />}
            style={{ flexShrink: 0 }}
          />
        </div>
      }
      extra={extra && <div style={{ marginLeft: token.marginXS }}>{extra}</div>}
    >
      {keepMounted ? (
        <div style={{ display: collapsed ? "none" : undefined }}>{children}</div>
      ) : (
        !collapsed && children
      )}
    </Card>
  );
}
