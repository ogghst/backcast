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
import { CostElementsService, ProjectsService, WbesService } from "@/client"
import PendingItems from "@/components/Pending/PendingItems"
import CostRegistrationsTable from "@/components/Projects/CostRegistrationsTable"
import CostSummary from "@/components/Projects/CostSummary"

const costElementDetailSearchSchema = z.object({
  tab: z
    .enum(["info", "cost-registrations", "cost-summary"])
    .catch("cost-registrations"),
})

const _PER_PAGE = 10

function getProjectQueryOptions({ id }: { id: string }) {
  return {
    queryFn: () => ProjectsService.readProject({ id }),
    queryKey: ["projects", id],
  }
}

function getWBEQueryOptions({ id }: { id: string }) {
  return {
    queryFn: () => WbesService.readWbe({ id }),
    queryKey: ["wbes", id],
  }
}

function getCostElementQueryOptions({ id }: { id: string }) {
  return {
    queryFn: () => CostElementsService.readCostElement({ id }),
    queryKey: ["cost-elements", id],
  }
}

export const Route = createFileRoute(
  "/_layout/projects/$id/wbes/$wbeId/cost-elements/$costElementId",
)({
  component: CostElementDetail,
  validateSearch: (search) => costElementDetailSearchSchema.parse(search),
})

function CostElementDetail() {
  const { id: projectId, wbeId, costElementId } = Route.useParams()
  const navigate = useNavigate({ from: Route.fullPath })
  const { tab } = Route.useSearch()

  const { data: project, isLoading: isLoadingProject } = useQuery({
    ...getProjectQueryOptions({ id: projectId }),
  })

  const { data: wbe, isLoading: isLoadingWBE } = useQuery({
    ...getWBEQueryOptions({ id: wbeId }),
  })

  const { data: costElement, isLoading: isLoadingCostElement } = useQuery({
    ...getCostElementQueryOptions({ id: costElementId }),
  })

  const handleTabChange = (value: string) => {
    navigate({
      search: (prev) => ({
        ...prev,
        tab: value as "info" | "cost-registrations" | "cost-summary",
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

      <Heading size="lg" mb={4}>
        {costElement.department_name} ({costElement.department_code})
      </Heading>

      <Tabs.Root
        value={tab}
        onValueChange={({ value }) => handleTabChange(value)}
        variant="subtle"
        mt={4}
      >
        <Tabs.List>
          <Tabs.Trigger value="info">Cost Element Information</Tabs.Trigger>
          <Tabs.Trigger value="cost-registrations">
            Cost Registrations
          </Tabs.Trigger>
          <Tabs.Trigger value="cost-summary">Cost Summary</Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="info">
          <Box mt={4}>
            <Text color="fg.muted">
              Cost element information content will be added here.
            </Text>
          </Box>
        </Tabs.Content>

        <Tabs.Content value="cost-registrations">
          <Box mt={4}>
            <CostRegistrationsTable costElementId={costElementId} />
          </Box>
        </Tabs.Content>

        <Tabs.Content value="cost-summary">
          <Box mt={4}>
            <CostSummary level="cost-element" costElementId={costElementId} />
          </Box>
        </Tabs.Content>
      </Tabs.Root>
    </Container>
  )
}
