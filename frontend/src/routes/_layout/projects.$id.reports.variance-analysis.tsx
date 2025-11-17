import { Container } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import VarianceAnalysisReport from "@/components/Reports/VarianceAnalysisReport"

export const Route = createFileRoute(
  "/_layout/projects/$id/reports/variance-analysis",
)({
  component: VarianceAnalysisReportPage,
})

function VarianceAnalysisReportPage() {
  const { id: projectId } = Route.useParams()

  return (
    <Container maxW="full" py={8}>
      <VarianceAnalysisReport projectId={projectId} />
    </Container>
  )
}
