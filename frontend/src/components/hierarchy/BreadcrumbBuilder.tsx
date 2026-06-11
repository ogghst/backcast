import { Breadcrumb, Skeleton, theme } from "antd";
import { Link } from "react-router-dom";
import { HomeOutlined } from "@ant-design/icons";

interface BreadcrumbProject {
  project_id: string;
  code: string;
  name?: string;
}

interface BreadcrumbWBE {
  wbs_element_id: string;
  code: string;
  name: string;
}

export interface WBEBreadcrumb {
  project: BreadcrumbProject;
  wbe_path: BreadcrumbWBE[];
}

interface BreadcrumbBuilderProps {
  breadcrumb?: WBEBreadcrumb;
  loading?: boolean;
}

export const BreadcrumbBuilder = ({
  breadcrumb,
  loading,
}: BreadcrumbBuilderProps) => {
  const { token } = theme.useToken();
  if (loading) {
    return <Skeleton.Input active style={{ width: 300, marginBottom: token.marginMD }} />;
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

  // Dedup: if the first WBE in the path has the same code as the project,
  // we can rely on the WBE breadcrumb item for navigation and skip the project-level item
  // to avoid "ProjectCode / ProjectCode / ..."
  const firstWbeCode = breadcrumb.wbe_path[0]?.code;
  const showProjectItem = firstWbeCode !== breadcrumb.project.code;

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
    // WBE path items
    ...breadcrumb.wbe_path.map((wbe: BreadcrumbWBE, idx: number) => {
      const isLast = idx === breadcrumb.wbe_path.length - 1;
      return {
        title: isLast ? (
          <span style={{ fontWeight: 600 }}>
            {wbe.code} {wbe.name}
          </span>
        ) : (
          <Link
            to={`/projects/${breadcrumb.project.project_id}/wbs-elements/${wbe.wbs_element_id}`}
          >
            {wbe.code}
          </Link>
        ),
      };
    }),
  ];

  return <Breadcrumb items={items} style={{ marginBottom: token.marginMD }} />;
};
