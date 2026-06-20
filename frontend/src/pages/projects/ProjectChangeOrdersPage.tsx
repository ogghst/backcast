import { useParams } from "react-router-dom";
import { ChangeOrderList } from "@/features/change-orders";
import { ChangeOrderAnalytics } from "@/features/change-orders/components/ChangeOrderAnalytics";
import { Tabs } from "antd";
import { useState } from "react";
import { ProjectPage } from "@/features/projects/components/ProjectPage";

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

  return (
    <ProjectPage title="Change Orders">
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
    </ProjectPage>
  );
};
