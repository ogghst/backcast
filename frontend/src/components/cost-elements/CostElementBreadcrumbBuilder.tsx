import { Breadcrumb, Skeleton, Typography, Grid } from "antd";
import { Link } from "react-router-dom";
import { HomeOutlined } from "@ant-design/icons";

const { Text } = Typography;

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
  isMobile?: boolean;
}

export const CostElementBreadcrumbBuilder = ({
  breadcrumb,
  loading,
  isMobile: isMobileProp,
}: CostElementBreadcrumbBuilderProps) => {
  const screens = Grid.useBreakpoint();
  const isMobile = isMobileProp ?? !screens.sm;

  if (loading) {
    return <Skeleton.Input active style={{ width: 300, marginBottom: isMobile ? 8 : 16 }} />;
  }

  if (!breadcrumb) {
    return null;
  }

  const showProjectItem = breadcrumb.wbe.code !== breadcrumb.project.code;

  const projectItem = {
    title: (
      <Link to={`/projects/${breadcrumb.project.project_id}`}>
        {isMobile ? (
          <Text ellipsis style={{ maxWidth: 80, fontSize: 12 }}>
            {breadcrumb.project.code}
          </Text>
        ) : (
          breadcrumb.project.code
        )}
      </Link>
    ),
  };

  const items = [
    {
      title: (
        <Link to="/">
          <HomeOutlined style={{ fontSize: isMobile ? 12 : 14 }} /> {!isMobile && "Home"}
        </Link>
      ),
    },
    !isMobile ? {
      title: <Link to="/projects">Projects</Link>,
    } : null,
    ...(showProjectItem ? [projectItem] : []),
    {
      title: (
        <Link
          to={`/projects/${breadcrumb.project.project_id}/wbes/${breadcrumb.wbe.wbe_id}`}
        >
          {isMobile ? (
            <Text ellipsis style={{ maxWidth: 60, fontSize: 12 }}>
              {breadcrumb.wbe.code}
            </Text>
          ) : (
            breadcrumb.wbe.code
          )}
        </Link>
      ),
    },
    {
      title: (
        <span style={{ fontWeight: 600 }}>
          {isMobile ? (
            <Text ellipsis style={{ maxWidth: 100, fontSize: 12 }}>
              {breadcrumb.cost_element.code}
            </Text>
          ) : (
            <>
              {breadcrumb.cost_element.code} {breadcrumb.cost_element.name}
            </>
          )}
        </span>
      ),
    },
  ].filter(Boolean);

  return (
    <Breadcrumb
      items={items}
      style={{
        marginBottom: isMobile ? 8 : 16,
        fontSize: isMobile ? 12 : 14,
      }}
      separator={isMobile ? "/" : "/"}
    />
  );
};
