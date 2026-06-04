import { useParams } from "react-router-dom";
import { Typography, Card, Row, Col, theme } from "antd";
import { BudgetSettingsWidget } from "@/features/projects/widgets/BudgetSettingsWidget";
import { ProjectConfigPanel } from "@/features/change-orders/components/ProjectConfigPanel";
import { Can } from "@/components/auth/Can";

const { Title } = Typography;

/**
 * ProjectAdminPage Component
 *
 * Provides administrative configuration options for a project:
 * - Budget Settings (warning threshold, admin override)
 * - Future: Other admin settings as needed
 *
 * Requires project-budget-settings-read permission to view.
 */
export const ProjectAdminPage = () => {
  const { token } = theme.useToken();
  const { projectId } = useParams<{ projectId: string }>();

  if (!projectId) {
    return (
      <div style={{ padding: `${token.paddingXL}px 0` }}>
        <Title level={2}>Project Administration</Title>
        <Card>
          <Typography.Text type="secondary">
            Project ID is required. Please navigate to this page from a valid project.
          </Typography.Text>
        </Card>
      </div>
    );
  }

  return (
    <div style={{ padding: `${token.paddingXL}px 0` }}>
      <Title level={2} style={{ marginBottom: token.paddingLG }}>
        Project Administration
      </Title>

      <Row gutter={[token.paddingLG, token.paddingLG]}>
        <Col xs={24} lg={12} xl={8}>
          <Can permission="project-budget-settings-read">
            <BudgetSettingsWidget
              projectId={projectId}
              onSuccess={() => {
                // Optionally refetch or show success message
              }}
            />
          </Can>
        </Col>
      </Row>

      <Row gutter={[token.paddingLG, token.paddingLG]} style={{ marginTop: token.paddingLG }}>
        <Col xs={24}>
          <ProjectConfigPanel projectId={projectId} />
        </Col>
      </Row>
    </div>
  );
};

export default ProjectAdminPage;
