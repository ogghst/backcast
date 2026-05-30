import { Breadcrumb, Skeleton } from "antd";
import { Link } from "react-router-dom";
import { HomeOutlined } from "@ant-design/icons";
import type { WorkPackageBreadcrumb } from "@/features/work-packages/api/useWorkPackages";

interface WorkPackageBreadcrumbBuilderProps {
  breadcrumb?: WorkPackageBreadcrumb;
  loading?: boolean;
}

export const WorkPackageBreadcrumbBuilder = ({
  breadcrumb,
  loading,
}: WorkPackageBreadcrumbBuilderProps) => {
  if (loading) {
    return <Skeleton.Input active style={{ width: 300, marginBottom: 16 }} />;
  }

  if (!breadcrumb) {
    return null;
  }

  const projectItem = {
    title: (
      <Link to={`/projects/${breadcrumb.project.project_id}`}>
        {breadcrumb.project.code}
      </Link>
    ),
  };

  // Dedup: if WBS code === project code, skip the project-level item
  const showProjectItem = breadcrumb.wbs_element.code !== breadcrumb.project.code;

  const items = [
    {
      title: (
        <Link to="/">
          <HomeOutlined /> Home
        </Link>
      ),
    },
    {
      title: <Link to="/projects">Projects</Link>,
    },
    ...(showProjectItem ? [projectItem] : []),
    {
      title: (
        <Link
          to={`/projects/${breadcrumb.project.project_id}/wbs-elements/${breadcrumb.wbs_element.wbs_element_id}`}
        >
          {breadcrumb.wbs_element.code}
        </Link>
      ),
    },
    {
      title: (
        <span style={{ fontWeight: 600 }}>
          {breadcrumb.work_package.code} {breadcrumb.work_package.name}
        </span>
      ),
    },
  ];

  return <Breadcrumb items={items} style={{ marginBottom: 16 }} />;
};
