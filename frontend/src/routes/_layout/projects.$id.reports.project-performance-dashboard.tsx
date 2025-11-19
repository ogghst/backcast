import { Container } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import ProjectPerformanceDashboard from "@/components/Reports/ProjectPerformanceDashboard"

export const Route = createFileRoute(
  "/_layout/projects/$id/reports/project-performance-dashboard",
)({
  component: ProjectPerformanceDashboardPage,
})

function ProjectPerformanceDashboardPage() {
  const { id: projectId } = Route.useParams()

  return (
    <Container maxW="full" py={8}>
      <ProjectPerformanceDashboard projectId={projectId} />
    </Container>
  )
}
