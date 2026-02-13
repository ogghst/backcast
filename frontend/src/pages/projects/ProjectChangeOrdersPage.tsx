import { useParams, Link } from "react-router-dom";
import { useProject } from "@/features/projects/api/useProjects";
import { ChangeOrderList } from "@/features/change-orders";
import { Breadcrumb } from "antd";

/**
 * ProjectChangeOrdersPage component
 *
 * Dedicated page for viewing and managing change orders for a project.
 * This page is accessed via the "Change Orders" tab in the project navigation.
 */
export const ProjectChangeOrdersPage = () => {
  const { projectId } = useParams<{ projectId: string }>();

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
      <ChangeOrderList projectId={projectId!} />
    </div>
  );
};
