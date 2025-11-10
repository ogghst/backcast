import { Box, Container, Heading, Text, VStack } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"
import { FiChevronRight } from "react-icons/fi"
import type { CostElementWithSchedulePublic } from "@/client"
import { BudgetTimelineService, ProjectsService } from "@/client"
import BudgetTimeline from "@/components/Projects/BudgetTimeline"
import BudgetTimelineFilter from "@/components/Projects/BudgetTimelineFilter"

export const Route = createFileRoute("/_layout/projects/$id/budget-timeline")({
  component: BudgetTimelinePage,
})

function getProjectQueryOptions({ id }: { id: string }) {
  return {
    queryFn: () => ProjectsService.readProject({ id }),
    queryKey: ["projects", id],
  }
}

function BudgetTimelinePage() {
  const params = Route.useParams() as { id: string }
  const { id: projectId } = params
  const [filter, setFilter] = useState<{
    wbeIds?: string[]
    costElementIds?: string[]
    costElementTypeIds?: string[]
  }>({})
  // Fetch project data
  const { data: project, isLoading: isLoadingProject } = useQuery(
    getProjectQueryOptions({ id: projectId }),
  )

  // Fetch cost elements with schedules based on filter
  // Normalize filter arrays for consistent query key comparison
  const normalizedFilter = {
    wbeIds: filter.wbeIds?.length ? [...filter.wbeIds].sort() : undefined,
    costElementIds: filter.costElementIds?.length
      ? [...filter.costElementIds].sort()
      : undefined,
    costElementTypeIds: filter.costElementTypeIds?.length
      ? [...filter.costElementTypeIds].sort()
      : undefined,
  }

  const { data: costElements, isLoading: isLoadingCostElements } = useQuery<
    CostElementWithSchedulePublic[]
  >({
    queryFn: () =>
      BudgetTimelineService.getCostElementsWithSchedules({
        projectId: projectId,
        wbeIds: normalizedFilter.wbeIds,
        costElementIds: normalizedFilter.costElementIds,
        costElementTypeIds: normalizedFilter.costElementTypeIds,
      }),
    queryKey: [
      "cost-elements-with-schedules",
      projectId,
      normalizedFilter.wbeIds,
      normalizedFilter.costElementIds,
      normalizedFilter.costElementTypeIds,
    ],
    enabled: !!projectId,
  })

  const handleFilterChange = (newFilter: {
    wbeIds?: string[]
    costElementIds?: string[]
    costElementTypeIds?: string[]
  }) => {
    setFilter(newFilter)
  }

  if (isLoadingProject) {
    return (
      <Container maxW="container.xl" py={8}>
        <Text>Loading project...</Text>
      </Container>
    )
  }

  if (!project) {
    return (
      <Container maxW="container.xl" py={8}>
        <Text>Project not found</Text>
      </Container>
    )
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack gap={6} align="stretch">
        {/* Breadcrumb Navigation */}
        <Box>
          <Link
            to="/projects/$id"
            params={{ id: projectId } as any}
            search={{ page: 1, tab: "wbes" } as any}
            style={{ textDecoration: "none" }}
          >
            <Text
              fontSize="sm"
              color="fg.muted"
              _hover={{ color: "fg.default", textDecoration: "underline" }}
              display="inline-flex"
              alignItems="center"
              gap={1}
            >
              {project.project_name}
              <FiChevronRight />
            </Text>
          </Link>
          <Heading size="lg" mt={2}>
            Budget Timeline
          </Heading>
          <Text fontSize="sm" color="fg.muted" mt={2}>
            Visualize how budget is distributed over time for selected cost
            elements
          </Text>
        </Box>

        {/* Filter Interface */}
        <BudgetTimelineFilter
          projectId={projectId}
          context="standalone"
          onFilterChange={handleFilterChange}
        />

        {/* Timeline Visualization */}
        {isLoadingCostElements ? (
          <Box p={4} borderWidth="1px" borderRadius="lg" bg="bg.surface">
            <Text>Loading cost elements...</Text>
          </Box>
        ) : costElements && costElements.length === 0 ? (
          <Box p={4} borderWidth="1px" borderRadius="lg" bg="bg.surface">
            <Text color="fg.muted">
              No cost elements found matching the selected filters. Please
              adjust your filter selections.
            </Text>
          </Box>
        ) : (
          <BudgetTimeline
            costElements={costElements || []}
            viewMode="aggregated"
            projectId={projectId}
            wbeIds={normalizedFilter.wbeIds}
            costElementIds={normalizedFilter.costElementIds}
          />
        )}
      </VStack>
    </Container>
  )
}
