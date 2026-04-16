import { useParams } from "react-router-dom";
import { Typography, Card, Row, Col, theme } from "antd";
import { BudgetSettingsWidget } from "@/features/projects/widgets/BudgetSettingsWidget";
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
      <div style={{ padding: token.paddingXL }}>
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
    <div style={{ padding: token.paddingXL }}>
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

      {/* Placeholder for future admin settings */}
      {/* <Row gutter={[token.paddingLG, token.paddingLG]} style={{ marginTop: token.paddingXL }}>
        <Col xs={24} lg={12} xl={8}>
          <Card title="More Admin Settings">
            <Typography.Text type="secondary">
              Additional administrative settings can be added here in the future.
            </Typography.Text>
          </Card>
        </Col>
      </Row> */}
    </div>
  );
};

export default ProjectAdminPage;
