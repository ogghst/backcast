import { useParams, Link } from "react-router-dom";
import { useProject } from "@/features/projects/api/useProjects";
import { ChangeOrderList } from "@/features/change-orders";
import { ChangeOrderAnalytics } from "@/features/change-orders/components/ChangeOrderAnalytics";
import { Breadcrumb, Tabs } from "antd";
import { useState } from "react";

/**
 * ProjectChangeOrdersPage component
 *
 * Dedicated page for viewing and managing change orders for a project.
 * This page is accessed via the "Change Orders" tab in the project navigation.
 *
 * Provides two views:
 * - List View: Table of all change orders with filtering
 * - Analytics View: Dashboard with statistics and charts
 */
export const ProjectChangeOrdersPage = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [activeTab, setActiveTab] = useState("list");

  const { data: project } = useProject(projectId!);

  return (
    <div style={{ padding: 24 }}>
      <Breadcrumb
        items={[
          { title: <Link to="/">Home</Link> },
          { title: <Link to="/projects">Projects</Link> },
          { title: project?.code || "Project" },
          { title: "Change Orders" },
        ]}
        style={{ marginBottom: 16 }}
      />
      <h1 style={{ margin: 0, marginBottom: 16 }}>Change Orders</h1>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: "list",
            label: "List View",
            children: <ChangeOrderList projectId={projectId!} />,
          },
          {
            key: "analytics",
            label: "Analytics View",
            children: (
              <ChangeOrderAnalytics
                projectId={projectId!}
                branch="main"
              />
            ),
          },
        ]}
      />
    </div>
  );
};
