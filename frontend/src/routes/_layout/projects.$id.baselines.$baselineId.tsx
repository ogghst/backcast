import { Box, Container, Flex, Heading, Tabs, Text } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { FiChevronRight } from "react-icons/fi"
import { z } from "zod"
import { BaselineLogsService, ProjectsService } from "@/client"
import AIChat from "@/components/Projects/AIChat"
import BaselineCostElementsByWBETable from "@/components/Projects/BaselineCostElementsByWBETable"
import BaselineCostElementsTable from "@/components/Projects/BaselineCostElementsTable"
import BaselineEarnedValueEntriesTable from "@/components/Projects/BaselineEarnedValueEntriesTable"
import BaselineSummary from "@/components/Projects/BaselineSummary"
import { useColorModeValue } from "@/components/ui/color-mode"
import { useTimeMachine } from "@/context/TimeMachineContext"

const BASELINE_TAB_OPTIONS = [
  "summary",
  "by-wbe",
  "all-cost-elements",
  "earned-value",
  "ai-assessment",
] as const

type BaselineDetailTab = (typeof BASELINE_TAB_OPTIONS)[number]

const baselineDetailSearchSchema = z.object({
  baselineTab: z.enum(BASELINE_TAB_OPTIONS).catch("by-wbe"),
})

export const Route = createFileRoute(
  "/_layout/projects/$id/baselines/$baselineId",
)({
  component: BaselineDetail,
  validateSearch: (search) => baselineDetailSearchSchema.parse(search),
})

function getProjectQueryOptions({
  id,
  controlDate,
}: {
  id: string
  controlDate: string
}) {
  return {
    queryFn: () => ProjectsService.readProject({ id }),
    queryKey: ["projects", id, controlDate],
  }
}

function getBaselineQueryOptions({
  projectId,
  baselineId,
  controlDate,
}: {
  projectId: string
  baselineId: string
  controlDate: string
}) {
  return {
    queryFn: () =>
      BaselineLogsService.readBaselineLog({
        projectId,
        baselineId,
      }),
    queryKey: ["baseline-logs", projectId, baselineId, controlDate],
  }
}

function BaselineDetail() {
  const { id: projectId, baselineId } = Route.useParams()
  const { baselineTab } = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  const { controlDate } = useTimeMachine()
  const mutedText = useColorModeValue("fg.muted", "fg.muted")

  const handleTabChange = (value: string) => {
    navigate({
      search: (prev) => ({
        ...prev,
        baselineTab: value as BaselineDetailTab,
      }),
    })
  }

  // Fetch project data
  const { data: project, isLoading: isLoadingProject } = useQuery(
    getProjectQueryOptions({ id: projectId, controlDate }),
  )

  // Fetch baseline data
  const { data: baseline, isLoading: isLoadingBaseline } = useQuery(
    getBaselineQueryOptions({
      projectId,
      baselineId,
      controlDate,
    }),
  )

  if (isLoadingProject || isLoadingBaseline) {
    return (
      <Container maxW="container.xl" py={8}>
        <Text>Loading...</Text>
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

  if (!baseline) {
    return (
      <Container maxW="container.xl" py={8}>
        <Text>Baseline not found</Text>
      </Container>
    )
  }

  // Get baseline display name
  const baselineDisplayName =
    baseline.description ||
    `${baseline.baseline_type} - ${baseline.baseline_date}`

  return (
    <Container maxW="full" py={8}>
      {/* Breadcrumb Navigation */}
      <Flex alignItems="center" gap={2} mb={4} flexWrap="wrap">
        <Link to="/projects" search={{ page: 1 }}>
          <Text
            fontSize="sm"
            color="blue.500"
            _hover={{ textDecoration: "underline" }}
          >
            Projects
          </Text>
        </Link>
        <FiChevronRight />
        <Link
          to="/projects/$id"
          params={{ id: project.project_id }}
          search={{ page: 1, tab: "baselines" } as any}
        >
          <Text
            fontSize="sm"
            color="blue.500"
            _hover={{ textDecoration: "underline" }}
          >
            {project.project_name}
          </Text>
        </Link>
        <FiChevronRight />
        <Text fontSize="sm" color="gray.600">
          {baselineDisplayName}
        </Text>
      </Flex>

      <Heading size="lg" mb={2}>
        Baseline: {baselineDisplayName}
      </Heading>
      {baseline.description && (
        <Text fontSize="sm" color={mutedText} mb={4}>
          {baseline.description}
        </Text>
      )}

      {/* Tabbed Content */}
      <Tabs.Root
        value={baselineTab}
        onValueChange={({ value }) => handleTabChange(value || "by-wbe")}
        variant="subtle"
        mt={4}
      >
        <Tabs.List>
          <Tabs.Trigger value="summary">Summary</Tabs.Trigger>
          <Tabs.Trigger value="by-wbe">By WBE</Tabs.Trigger>
          <Tabs.Trigger value="all-cost-elements">
            All Cost Elements
          </Tabs.Trigger>
          <Tabs.Trigger value="earned-value">Earned Value</Tabs.Trigger>
          <Tabs.Trigger value="ai-assessment">AI Assessment</Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="summary">
          <Box mt={4}>
            <BaselineSummary projectId={projectId} baselineId={baselineId} />
          </Box>
        </Tabs.Content>

        <Tabs.Content value="by-wbe">
          <Box mt={4}>
            <BaselineCostElementsByWBETable
              projectId={projectId}
              baselineId={baselineId}
            />
          </Box>
        </Tabs.Content>

        <Tabs.Content value="all-cost-elements">
          <Box mt={4}>
            <BaselineCostElementsTable
              projectId={projectId}
              baselineId={baselineId}
            />
          </Box>
        </Tabs.Content>

        <Tabs.Content value="earned-value">
          <Box mt={4}>
            <BaselineEarnedValueEntriesTable
              projectId={projectId}
              baselineId={baselineId}
            />
          </Box>
        </Tabs.Content>

        <Tabs.Content value="ai-assessment">
          <Box mt={4} h="calc(100vh - 400px)" minH="400px">
            <AIChat contextType="baseline" contextId={baselineId} />
          </Box>
        </Tabs.Content>
      </Tabs.Root>
    </Container>
  )
}
