import { Breadcrumb, Skeleton } from "antd";
import { Link } from "react-router-dom";
import { HomeOutlined } from "@ant-design/icons";

export interface CostElementBreadcrumb {
  project: {
    id: string;
    project_id: string;
    code: string;
    name: string;
  };
  wbe: {
    id: string;
    wbe_id: string;
    code: string;
    name: string;
  };
  cost_element: {
    id: string;
    cost_element_id: string;
    code: string;
    name: string;
  };
}

interface CostElementBreadcrumbBuilderProps {
  breadcrumb?: CostElementBreadcrumb;
  loading?: boolean;
}

export const CostElementBreadcrumbBuilder = ({
  breadcrumb,
  loading,
}: CostElementBreadcrumbBuilderProps) => {
  if (loading) {
    return <Skeleton.Input active style={{ width: 300, marginBottom: 16 }} />;
  }

  if (!breadcrumb) {
    return null;
  }

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
    {
      title: (
        <Link to={`/projects/${breadcrumb.project.project_id}`}>
          {breadcrumb.project.code}
        </Link>
      ),
    },
    {
      title: (
        <Link
          to={`/projects/${breadcrumb.project.project_id}/wbes/${breadcrumb.wbe.wbe_id}`}
        >
          {breadcrumb.wbe.code}
        </Link>
      ),
    },
    {
      title: (
        <span style={{ fontWeight: 600 }}>
          {breadcrumb.cost_element.code} {breadcrumb.cost_element.name}
        </span>
      ),
    },
  ];

  return <Breadcrumb items={items} style={{ marginBottom: 16 }} />;
};
