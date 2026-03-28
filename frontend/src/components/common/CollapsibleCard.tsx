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
      {!collapsed && children}
    </Card>
  );
}
