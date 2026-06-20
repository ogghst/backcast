import React from "react";
import { Outlet, useParams, useNavigate } from "react-router-dom";
import { Button } from "antd";
import { RobotOutlined } from "@ant-design/icons";
import { PageNavigation } from "@/components/navigation";
import { Can } from "@/components/auth/Can";

export const ProjectLayout: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const items = [
    { key: "dashboard", label: "Dashboard", path: `/projects/${projectId}/dashboard` },
    { key: "overview", label: "Overview", path: `/projects/${projectId}` },
    { key: "structure", label: "Structure", path: `/projects/${projectId}/structure` },
    // Explorer tab temporarily disabled
    // { key: "explorer", label: "Explorer", path: `/projects/${projectId}/explorer` },
    { key: "schedule", label: "Schedule", path: `/projects/${projectId}/schedule` },
    { key: "change-orders", label: "Change Orders", path: `/projects/${projectId}/change-orders` },
    { key: "members", label: "Members", path: `/projects/${projectId}/members` },
    { key: "evm-analysis", label: "EVM Analysis", path: `/projects/${projectId}/evm-analysis` },
    { key: "coq-analysis", label: "COQ Analysis", path: `/projects/${projectId}/coq-analysis` },
    { key: "cost-events", label: "Cost Events", path: `/projects/${projectId}/cost-events` },
    { key: "documents", label: "Documents", path: `/projects/${projectId}/documents` },
    { key: "admin", label: "Admin", path: `/projects/${projectId}/admin` },
  ];

  const handleOpenChat = () => {
    navigate(`/chat?ctx=project:${projectId}`, {
      state: { returnTo: `/projects/${projectId}` },
    });
  };

  return (
    <>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <PageNavigation items={items} />
        <Can permission="ai-chat">
          <Button
            icon={<RobotOutlined />}
            onClick={handleOpenChat}
          >
            AI Chat
          </Button>
        </Can>
      </div>
      <Outlet />
    </>
  );
};
