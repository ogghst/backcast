import { Menu, Affix } from "antd";
import { Link, useParams } from "react-router-dom";
import {
  FileTextOutlined,
  SyncOutlined,
  BarChartOutlined,
  RadarChartOutlined,
} from "@ant-design/icons";

interface ChangeOrderPageNavProps {
  createMode: boolean;
}

/**
 * ChangeOrderPageNav - Sticky navigation with anchor links.
 *
 * Shows:
 * - "Details" - Links to form section
 * - "Workflow" - Links to workflow section (hidden in create mode)
 * - "Impact" - Links to impact section (hidden in create mode)
 * - "Full Analysis" - Links to dedicated impact analysis page (hidden in create mode)
 *
 * Stays fixed at the top while scrolling.
 */
export function ChangeOrderPageNav({
  createMode,
}: ChangeOrderPageNavProps): JSX.Element | null {
  const { projectId, changeOrderId } = useParams<{
    projectId: string;
    changeOrderId?: string;
  }>();

  const menuItems = [
    {
      key: "details",
      icon: <FileTextOutlined />,
      label: <Link to="#details">Details</Link>,
    },
    ...(createMode
      ? []
      : [
          {
            key: "workflow",
            icon: <SyncOutlined />,
            label: <Link to="#workflow">Workflow</Link>,
          },
          {
            key: "impact",
            icon: <BarChartOutlined />,
            label: <Link to="#impact">Impact</Link>,
          },
          {
            key: "full-analysis",
            icon: <RadarChartOutlined />,
            label: (
              <Link
                to={`/projects/${projectId}/change-orders/${changeOrderId}/impact`}
              >
                Full Analysis
              </Link>
            ),
          },
        ]),
  ];

  return (
    <Affix offsetTop={0}>
      <div
        style={{
          background: "#fff",
          borderBottom: "1px solid #f0f0f0",
          padding: "8px 24px",
          marginBottom: 16,
        }}
      >
        <Menu
          mode="horizontal"
          items={menuItems}
          style={{ border: "none" }}
          selectedKeys={[]}
        />
      </div>
    </Affix>
  );
}
