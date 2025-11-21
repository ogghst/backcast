import {
  Box,
  Container,
  EmptyState,
  Flex,
  Heading,
  Tabs,
  Text,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { z } from "zod"
import type { CostElementWithSchedulePublic } from "@/client"
import {
  BudgetTimelineService,
  CostElementsService,
  ProjectsService,
  WbesService,
} from "@/client"
import PendingItems from "@/components/Pending/PendingItems"
import AIChat from "@/components/Projects/AIChat"
import BudgetTimeline from "@/components/Projects/BudgetTimeline"
import CostElementSchedulesTable from "@/components/Projects/CostElementSchedulesTable"
import CostRegistrationsTable from "@/components/Projects/CostRegistrationsTable"
import EarnedValueEntriesTable from "@/components/Projects/EarnedValueEntriesTable"
import EarnedValueSummary from "@/components/Projects/EarnedValueSummary"
import MetricsSummary from "@/components/Projects/MetricsSummary"
import { useTimeMachine } from "@/context/TimeMachineContext"

const COST_ELEMENT_VIEW_OPTIONS = [
  "info",
  "cost-registrations",
  "schedule",
  "earned-value",
  "metrics",
  "timeline",
  "ai-assessment",
] as const

export type CostElementView = (typeof COST_ELEMENT_VIEW_OPTIONS)[number]

const DEFAULT_COST_ELEMENT_VIEW: CostElementView = "cost-registrations"

const costElementDetailSearchSchema = z.object({
  view: z.enum(COST_ELEMENT_VIEW_OPTIONS).catch(DEFAULT_COST_ELEMENT_VIEW),
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

function getWBEQueryOptions({
  id,
  controlDate,
}: {
  id: string
  controlDate: string
}) {
  return {
    queryFn: () => WbesService.readWbe({ id }),
    queryKey: ["wbes", id, controlDate],
  }
}

function getCostElementQueryOptions({
  id,
  controlDate,
}: {
  id: string
  controlDate: string
}) {
  return {
    queryFn: () => CostElementsService.readCostElement({ id }),
    queryKey: ["cost-elements", id, controlDate],
  }
}

export const Route = createFileRoute(
  "/_layout/projects/$id/wbes/$wbeId/cost-elements/$costElementId",
)({
  component: CostElementDetail,
  validateSearch: (search) =>
    costElementDetailSearchSchema.parse({
      view:
        typeof search.view === "string"
          ? search.view
          : typeof search.tab === "string"
            ? search.tab
            : undefined,
    }),
})

function CostElementDetail() {
  const { id: projectId, wbeId, costElementId } = Route.useParams()
  const navigate = useNavigate({ from: Route.fullPath })
  const { view } = Route.useSearch()
  const { controlDate } = useTimeMachine()

  const { data: project, isLoading: isLoadingProject } = useQuery({
    ...getProjectQueryOptions({ id: projectId, controlDate }),
  })

  const { data: wbe, isLoading: isLoadingWBE } = useQuery({
    ...getWBEQueryOptions({ id: wbeId, controlDate }),
  })

  const { data: costElement, isLoading: isLoadingCostElement } = useQuery({
    ...getCostElementQueryOptions({ id: costElementId, controlDate }),
  })

  // Fetch cost element with schedule for timeline
  const { data: costElementsWithSchedule, isLoading: isLoadingCostElements } =
    useQuery<CostElementWithSchedulePublic[]>({
      queryFn: () =>
        BudgetTimelineService.getCostElementsWithSchedules({
          projectId: projectId,
          costElementIds: [costElementId],
        }),
      queryKey: [
        "cost-elements-with-schedules",
        projectId,
        costElementId,
        controlDate,
      ],
      enabled: !!projectId && !!costElementId,
    })

  const handleTabChange = (value: CostElementView) => {
    navigate({
      search: (prev) => ({
        ...prev,
        view: value,
      }),
    })
  }

  if (isLoadingProject || isLoadingWBE || isLoadingCostElement) {
    return (
      <Container maxW="full">
        <PendingItems />
      </Container>
    )
  }

  if (!project || !wbe || !costElement) {
    return (
      <Container maxW="full">
        <EmptyState.Root>
          <EmptyState.Content>
            <EmptyState.Title>Not Found</EmptyState.Title>
            <EmptyState.Description>
              The requested cost element could not be found.
            </EmptyState.Description>
          </EmptyState.Content>
        </EmptyState.Root>
      </Container>
    )
  }

  return (
    <Container maxW="full">
      <Flex alignItems="center" gap={2} mb={4} flexWrap="wrap">
        <Link
          to="/projects/$id"
          params={{ id: project.project_id } as any}
          search={{} as any}
        >
          <Text color="blue.500" _hover={{ textDecoration: "underline" }}>
            {project.project_name}
          </Text>
        </Link>
        <Text color="fg.muted">/</Text>
        <Link
          to="/projects/$id/wbes/$wbeId"
          params={{ id: project.project_id, wbeId: wbe.wbe_id } as any}
          search={{} as any}
        >
          <Text color="blue.500" _hover={{ textDecoration: "underline" }}>
            {wbe.machine_type}
          </Text>
        </Link>
        <Text color="fg.muted">/</Text>
        <Text color="fg.muted">{costElement.department_name}</Text>
      </Flex>

      <Heading size="lg" mb={1}>
        {costElement.department_name} ({costElement.department_code})
      </Heading>
      <Text color="fg.muted" mb={4}>
        Budget BAC: {costElement.budget_bac ?? "0.00"}
      </Text>

      <Tabs.Root
        value={view}
        onValueChange={({ value }) => handleTabChange(value as CostElementView)}
        variant="subtle"
        mt={4}
      >
        <Tabs.List>
          <Tabs.Trigger value="info">Cost Element Information</Tabs.Trigger>
          <Tabs.Trigger value="cost-registrations">
            Cost Registrations
          </Tabs.Trigger>
          <Tabs.Trigger value="schedule">Schedule</Tabs.Trigger>
          <Tabs.Trigger value="earned-value">Earned Value</Tabs.Trigger>
          <Tabs.Trigger value="metrics">Metrics</Tabs.Trigger>
          <Tabs.Trigger value="timeline">Timeline</Tabs.Trigger>
          <Tabs.Trigger value="ai-assessment">AI Assessment</Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="info">
          <Box mt={4} display="grid" gap={2}>
            <Text>
              <strong>Department:</strong> {costElement.department_name} (
              {costElement.department_code})
            </Text>
            <Text>
              <strong>Status:</strong> {costElement.status ?? "active"}
            </Text>
            <Text>
              <strong>Budget BAC:</strong> {costElement.budget_bac ?? "0.00"}
            </Text>
            <Text>
              <strong>Revenue Plan:</strong>{" "}
              {costElement.revenue_plan ?? "0.00"}
            </Text>
            {costElement.notes && (
              <Text>
                <strong>Notes:</strong> {costElement.notes}
              </Text>
            )}
          </Box>
        </Tabs.Content>

        <Tabs.Content value="cost-registrations">
          <Box mt={4}>
            <CostRegistrationsTable costElementId={costElementId} />
          </Box>
        </Tabs.Content>

        <Tabs.Content value="schedule">
          <Box mt={4}>
            <CostElementSchedulesTable costElementId={costElementId} />
          </Box>
        </Tabs.Content>

        <Tabs.Content value="earned-value">
          <Box mt={4}>
            <EarnedValueSummary
              level="cost-element"
              projectId={projectId}
              costElementId={costElementId}
            />
            <Box mt={6}>
              <EarnedValueEntriesTable
                costElementId={costElementId}
                budgetBac={costElement.budget_bac ?? null}
              />
            </Box>
          </Box>
        </Tabs.Content>

        <Tabs.Content value="metrics">
          <MetricsSummary
            level="cost-element"
            projectId={projectId}
            costElementId={costElementId}
          />
        </Tabs.Content>

        <Tabs.Content value="timeline">
          <Box mt={4}>
            <Heading size="md" mb={4}>
              Budget Timeline
            </Heading>
            {isLoadingCostElements ? (
              <Box
                p={4}
                borderWidth="1px"
                borderRadius="lg"
                bg="bg.surface"
                mt={4}
              >
                <Text>Loading cost element timeline...</Text>
              </Box>
            ) : costElementsWithSchedule &&
              costElementsWithSchedule.length === 0 ? (
              <Box
                p={4}
                borderWidth="1px"
                borderRadius="lg"
                bg="bg.surface"
                mt={4}
              >
                <Text color="fg.muted">
                  No schedule found for this cost element. Please add a schedule
                  to view the timeline.
                </Text>
              </Box>
            ) : (
              <Box mt={4}>
                <BudgetTimeline
                  costElements={costElementsWithSchedule || []}
                  viewMode="aggregated"
                  projectId={projectId}
                  costElementIds={[costElementId]}
                />
              </Box>
            )}
          </Box>
        </Tabs.Content>

        <Tabs.Content value="ai-assessment">
          <Box mt={4} h="calc(100vh - 300px)">
            <AIChat contextType="cost-element" contextId={costElementId} />
          </Box>
        </Tabs.Content>
      </Tabs.Root>
    </Container>
  )
}
