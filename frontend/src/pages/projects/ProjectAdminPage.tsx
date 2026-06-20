import { useParams } from "react-router-dom";
import { Card, Row, Col, theme } from "antd";
import { BudgetSettingsWidget } from "@/features/projects/widgets/BudgetSettingsWidget";
import { ProjectConfigPanel } from "@/features/change-orders/components/ProjectConfigPanel";
import { Can } from "@/components/auth/Can";
import { ProjectPage } from "@/features/projects/components/ProjectPage";

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
      <ProjectPage title="Project Administration">
        <Card>
          No project selected. Please navigate to this page from a valid
          project.
        </Card>
      </ProjectPage>
    );
  }

  return (
    <ProjectPage title="Project Administration">
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

      <Row
        gutter={[token.paddingLG, token.paddingLG]}
        style={{ marginTop: token.paddingLG }}
      >
        <Col xs={24}>
          <ProjectConfigPanel projectId={projectId} />
        </Col>
      </Row>
    </ProjectPage>
  );
};

export default ProjectAdminPage;
