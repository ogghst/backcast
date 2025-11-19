import {
  Box,
  Container,
  EmptyState,
  Flex,
  Heading,
  Tabs,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import {
  createFileRoute,
  Link,
  Outlet,
  useNavigate,
  useRouterState,
} from "@tanstack/react-router"
import { useState } from "react"
import { FiBox, FiChevronRight } from "react-icons/fi"
import { z } from "zod"
import type { CostElementWithSchedulePublic, WBEPublic } from "@/client"
import { BudgetTimelineService, ProjectsService, WbesService } from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import type { ColumnDefExtended } from "@/components/DataTable/types"
import PendingItems from "@/components/Pending/PendingItems"
import AddWBE from "@/components/Projects/AddWBE"
import BaselineLogsTable from "@/components/Projects/BaselineLogsTable"
import BudgetTimeline from "@/components/Projects/BudgetTimeline"
import BudgetTimelineFilter from "@/components/Projects/BudgetTimelineFilter"
import DeleteWBE from "@/components/Projects/DeleteWBE"
import EditWBE from "@/components/Projects/EditWBE"
import MetricsSummary from "@/components/Projects/MetricsSummary"
import { useTimeMachine } from "@/context/TimeMachineContext"

const projectDetailSearchSchema = z.object({
  page: z.number().catch(1),
  tab: z
    .enum([
      "info",
      "wbes",
      "summary",
      "cost-summary",
      "metrics",
      "timeline",
      "baselines",
    ])
    .catch("wbes"),
})

const PER_PAGE = 10

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

function getWBEsQueryOptions({
  projectId,
  page,
  controlDate,
}: {
  projectId: string
  page: number
  controlDate: string
}) {
  return {
    queryFn: () =>
      WbesService.readWbes({
        projectId: projectId,
        skip: (page - 1) * PER_PAGE,
        limit: PER_PAGE,
      }),
    queryKey: ["wbes", { projectId: projectId, page }, controlDate],
  }
}

export const Route = createFileRoute("/_layout/projects/$id")({
  component: ProjectDetail,
  validateSearch: (search) => projectDetailSearchSchema.parse(search),
})

// Column definitions for WBEs table
const wbesColumns: ColumnDefExtended<WBEPublic>[] = [
  {
    accessorKey: "machine_type",
    header: "Machine Type",
    enableSorting: true,
    enableResizing: true,
    enableColumnFilter: true,
    filterType: "text",
    size: 200,
    defaultVisible: true,
  },
  {
    accessorKey: "status",
    header: "Status",
    enableSorting: true,
    enableResizing: true,
    enableColumnFilter: true,
    filterType: "select",
    filterConfig: {
      type: "select",
      options: [
        "designing",
        "in-production",
        "shipped",
        "commissioning",
        "completed",
      ],
    },
    size: 120,
    defaultVisible: true,
    cell: ({ getValue }) => (
      <span style={{ textTransform: "capitalize" }}>
        {(getValue() as string) || "designing"}
      </span>
    ),
  },
  {
    accessorKey: "serial_number",
    header: "Serial Number",
    enableSorting: true,
    enableResizing: true,
    size: 150,
    defaultVisible: true,
    cell: ({ getValue }) => (getValue() as string) || "N/A",
  },
  {
    accessorKey: "revenue_allocation",
    header: "Revenue Allocation",
    enableSorting: true,
    enableResizing: true,
    size: 120,
    defaultVisible: true,
    cell: ({ getValue }) => (getValue() as string) || "0.00",
  },
  {
    accessorKey: "contracted_delivery_date",
    header: "Contracted Delivery",
    enableSorting: true,
    enableResizing: true,
    size: 150,
    defaultVisible: true,
    cell: ({ getValue }) =>
      getValue() ? new Date(getValue() as string).toLocaleDateString() : "N/A",
  },
  {
    id: "actions",
    header: "Actions",
    enableSorting: false,
    enableColumnFilter: false,
    size: 120,
    defaultVisible: true,
    cell: ({ row }) => (
      <Flex gap={2}>
        <EditWBE wbe={row.original} />
        <DeleteWBE
          id={row.original.wbe_id}
          machineType={row.original.machine_type}
        />
      </Flex>
    ),
  },
]

function WBEsTable({ projectId }: { projectId: string }) {
  const navigate = useNavigate({ from: Route.fullPath })
  const { page } = Route.useSearch()
  const { controlDate } = useTimeMachine()

  const { data, isLoading } = useQuery({
    ...getWBEsQueryOptions({ projectId, page, controlDate }),
    placeholderData: (prevData) => prevData,
  })

  const setPage = (page: number) => {
    navigate({
      search: (prev) => ({ ...prev, page }),
    })
  }

  const wbes = data?.data ?? []
  const count = data?.count ?? 0

  const handleRowClick = (wbe: WBEPublic) => {
    navigate({
      to: "/projects/$id/wbes/$wbeId",
      params: { id: projectId, wbeId: wbe.wbe_id },
      search: { page: 1 } as any,
    })
  }

  if (!isLoading && wbes.length === 0) {
    return (
      <EmptyState.Root>
        <EmptyState.Content>
          <EmptyState.Indicator>
            <FiBox />
          </EmptyState.Indicator>
          <VStack textAlign="center">
            <EmptyState.Title>No WBEs found</EmptyState.Title>
            <EmptyState.Description>
              This project has no Work Breakdown Elements yet
            </EmptyState.Description>
          </VStack>
        </EmptyState.Content>
      </EmptyState.Root>
    )
  }

  return (
    <DataTable
      data={wbes}
      columns={wbesColumns}
      tableId="wbes-table"
      onRowClick={handleRowClick}
      isLoading={isLoading}
      count={count}
      page={page}
      onPageChange={setPage}
      pageSize={PER_PAGE}
    />
  )
}

function ProjectDetail() {
  const { id } = Route.useParams()
  const navigate = useNavigate({ from: Route.fullPath })
  const location = useRouterState({
    select: (state) => state.location.pathname,
  })
  const isWBERoute = location.includes("/wbes/")
  const isBudgetTimelineRoute = location.includes("/budget-timeline")
  const isReportsRoute = location.includes("/reports/")

  const { tab } = Route.useSearch()
  const { controlDate } = useTimeMachine()
  const mappedTab =
    tab === "summary" || tab === "cost-summary" ? "metrics" : tab

  const { data: project, isLoading: isLoadingProject } = useQuery({
    ...getProjectQueryOptions({ id, controlDate }),
  })

  // Budget Timeline state - persists across tab switches
  const [filter, setFilter] = useState<{
    wbeIds?: string[]
    costElementIds?: string[]
    costElementTypeIds?: string[]
  }>({})
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
        projectId: id,
        wbeIds: normalizedFilter.wbeIds,
        costElementIds: normalizedFilter.costElementIds,
        costElementTypeIds: normalizedFilter.costElementTypeIds,
        // controlDate removed to match BudgetTimelineGetCostElementsWithSchedulesData type
      }),
    queryKey: [
      "cost-elements-with-schedules",
      id,
      normalizedFilter.wbeIds,
      normalizedFilter.costElementIds,
      normalizedFilter.costElementTypeIds,
      controlDate,
    ],
    enabled: !!id,
  })

  const handleFilterChange = (newFilter: {
    wbeIds?: string[]
    costElementIds?: string[]
    costElementTypeIds?: string[]
  }) => {
    setFilter(newFilter)
  }

  const handleTabChange = (value: string) => {
    navigate({
      search: (prev) => ({
        ...prev,
        tab: value as "info" | "wbes" | "metrics" | "timeline" | "baselines",
      }),
    })
  }

  if (isLoadingProject) {
    return (
      <Container maxW="full">
        <PendingItems />
      </Container>
    )
  }

  if (!project) {
    return (
      <Container maxW="full">
        <EmptyState.Root>
          <EmptyState.Content>
            <EmptyState.Title>Project not found</EmptyState.Title>
          </EmptyState.Content>
        </EmptyState.Root>
      </Container>
    )
  }

  // If we're on a WBE detail route or budget timeline route, render Outlet for child route
  if (isWBERoute || isBudgetTimelineRoute || isReportsRoute) {
    return <Outlet />
  }

  return (
    <Container maxW="full">
      <Flex alignItems="center" gap={2} pt={12} mb={2}>
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
        <Text fontSize="sm" color="gray.600">
          {project.project_name}
        </Text>
      </Flex>
      <Heading size="lg">{project.project_name}</Heading>

      <Tabs.Root
        value={mappedTab}
        onValueChange={({ value }) => handleTabChange(value)}
        variant="subtle"
        mt={4}
      >
        <Tabs.List>
          <Tabs.Trigger value="info">Project Information</Tabs.Trigger>
          <Tabs.Trigger value="wbes">Work Breakdown Elements</Tabs.Trigger>
          <Tabs.Trigger value="metrics">Metrics</Tabs.Trigger>
          <Tabs.Trigger value="timeline">Budget Timeline</Tabs.Trigger>
          <Tabs.Trigger value="baselines">Baselines</Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="info">
          <Box mt={4}>
            <Text color="fg.muted">
              Project information content will be added here.
            </Text>
          </Box>
        </Tabs.Content>

        <Tabs.Content value="wbes">
          <Box mt={4}>
            <Flex alignItems="center" justifyContent="space-between" mb={4}>
              <Heading size="md">Work Breakdown Elements</Heading>
              <AddWBE projectId={project.project_id} />
            </Flex>
            <WBEsTable projectId={project.project_id} />
          </Box>
        </Tabs.Content>

        <Tabs.Content value="metrics">
          <Box mt={4}>
            <Flex alignItems="center" justifyContent="space-between" mb={4}>
              <Heading size="md">Project Metrics</Heading>
              <Flex gap={4} alignItems="center">
                <Link
                  to="/projects/$id/reports/variance-analysis"
                  params={{ id: project.project_id } as any}
                  search={{} as any}
                >
                  <Text
                    fontSize="sm"
                    color="blue.500"
                    _hover={{ textDecoration: "underline" }}
                  >
                    View Variance Analysis Report →
                  </Text>
                </Link>
                <Link
                  to="/projects/$id/reports/cost-performance"
                  params={{ id: project.project_id } as any}
                  search={{} as any}
                >
                  <Text
                    fontSize="sm"
                    color="blue.500"
                    _hover={{ textDecoration: "underline" }}
                  >
                    View Cost Performance Report →
                  </Text>
                </Link>
                <Link
                  to="/projects/$id/reports/project-performance-dashboard"
                  params={{ id: project.project_id } as any}
                  search={{} as any}
                >
                  <Text
                    fontSize="sm"
                    color="blue.500"
                    _hover={{ textDecoration: "underline" }}
                  >
                    View Project Performance Dashboard →
                  </Text>
                </Link>
              </Flex>
            </Flex>
            <MetricsSummary level="project" projectId={project.project_id} />
          </Box>
        </Tabs.Content>

        <Tabs.Content value="timeline">
          <Box mt={4}>
            <Flex alignItems="center" justifyContent="space-between" mb={4}>
              <Heading size="md">Budget Timeline</Heading>
              <Link
                to="/projects/$id/budget-timeline"
                params={{ id: project.project_id } as any}
                search={{} as any}
              >
                <Text
                  fontSize="sm"
                  color="blue.500"
                  _hover={{ textDecoration: "underline" }}
                >
                  View Full Timeline →
                </Text>
              </Link>
            </Flex>
            <BudgetTimelineFilter
              projectId={project.project_id}
              context="project"
              onFilterChange={handleFilterChange}
            />
            {isLoadingCostElements ? (
              <Box
                p={4}
                borderWidth="1px"
                borderRadius="lg"
                bg="bg.surface"
                mt={4}
              >
                <Text>Loading cost elements...</Text>
              </Box>
            ) : costElements && costElements.length === 0 ? (
              <Box
                p={4}
                borderWidth="1px"
                borderRadius="lg"
                bg="bg.surface"
                mt={4}
              >
                <Text color="fg.muted">
                  No cost elements found matching the selected filters.
                </Text>
              </Box>
            ) : (
              <Box mt={4}>
                <BudgetTimeline
                  costElements={costElements || []}
                  viewMode="aggregated"
                  projectId={project.project_id}
                  wbeIds={normalizedFilter.wbeIds}
                  costElementIds={normalizedFilter.costElementIds}
                />
              </Box>
            )}
          </Box>
        </Tabs.Content>

        <Tabs.Content value="baselines">
          <Box mt={4}>
            <BaselineLogsTable projectId={project.project_id} />
          </Box>
        </Tabs.Content>
      </Tabs.Root>
    </Container>
  )
}
