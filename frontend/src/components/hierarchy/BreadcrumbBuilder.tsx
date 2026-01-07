import { Breadcrumb, Skeleton } from "antd";
import { Link } from "react-router-dom";
import { WBEBreadcrumb } from "@/api/generated";
import { HomeOutlined } from "@ant-design/icons";

interface BreadcrumbBuilderProps {
  breadcrumb?: WBEBreadcrumb;
  loading?: boolean;
}

export const BreadcrumbBuilder = ({
  breadcrumb,
  loading,
}: BreadcrumbBuilderProps) => {
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
    // WBE path items
    ...breadcrumb.wbe_path.map((wbe, idx) => {
      const isLast = idx === breadcrumb.wbe_path.length - 1;
      return {
        title: isLast ? (
          <span style={{ fontWeight: 600 }}>
            {wbe.code} {wbe.name}
          </span>
        ) : (
          <Link
            to={`/projects/${breadcrumb.project.project_id}/wbes/${wbe.wbe_id}`}
          >
            {wbe.code}
          </Link>
        ),
      };
    }),
  ];

  return <Breadcrumb items={items} style={{ marginBottom: 16 }} />;
};
