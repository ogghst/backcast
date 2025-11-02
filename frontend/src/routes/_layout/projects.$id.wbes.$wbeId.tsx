import {
  Box,
  Container,
  EmptyState,
  Flex,
  Heading,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { FiChevronRight, FiTag } from "react-icons/fi"
import { z } from "zod"

import { CostElementsService, ProjectsService, WbesService } from "@/client"
import PendingItems from "@/components/Pending/PendingItems"
import {
  PaginationItems,
  PaginationNextTrigger,
  PaginationPrevTrigger,
  PaginationRoot,
} from "@/components/ui/pagination.tsx"

const wbeDetailSearchSchema = z.object({
  page: z.number().catch(1),
})

const PER_PAGE = 10

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

function getCostElementsQueryOptions({
  wbeId,
  page,
}: {
  wbeId: string
  page: number
}) {
  return {
    queryFn: () =>
      CostElementsService.readCostElements({
        wbeId: wbeId,
        skip: (page - 1) * PER_PAGE,
        limit: PER_PAGE,
      }),
    queryKey: ["cost-elements", { wbeId: wbeId, page }],
  }
}

export const Route = createFileRoute("/_layout/projects/$id/wbes/$wbeId")({
  component: WBEDetail,
  validateSearch: (search) => wbeDetailSearchSchema.parse(search),
})

function CostElementsTable({ wbeId }: { wbeId: string }) {
  const navigate = useNavigate({ from: Route.fullPath })
  const { page } = Route.useSearch()

  const { data, isLoading, isPlaceholderData } = useQuery({
    ...getCostElementsQueryOptions({ wbeId, page }),
    placeholderData: (prevData) => prevData,
  })

  const setPage = (page: number) => {
    navigate({
      search: (prev) => ({ ...prev, page }),
    })
  }

  const costElements = data?.data.slice(0, PER_PAGE) ?? []
  const count = data?.count ?? 0

  if (isLoading) {
    return <PendingItems />
  }

  if (costElements.length === 0) {
    return (
      <EmptyState.Root>
        <EmptyState.Content>
          <EmptyState.Indicator>
            <FiTag />
          </EmptyState.Indicator>
          <VStack textAlign="center">
            <EmptyState.Title>No cost elements found</EmptyState.Title>
            <EmptyState.Description>
              This WBE has no cost elements yet
            </EmptyState.Description>
          </VStack>
        </EmptyState.Content>
      </EmptyState.Root>
    )
  }

  return (
    <>
      <Table.Root size={{ base: "sm", md: "md" }}>
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader w="md">Department</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Department Code</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Status</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Budget (BAC)</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Revenue Plan</Table.ColumnHeader>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {costElements?.map((ce) => (
            <Table.Row
              key={ce.cost_element_id}
              opacity={isPlaceholderData ? 0.5 : 1}
            >
              <Table.Cell truncate maxW="md">
                {ce.department_name}
              </Table.Cell>
              <Table.Cell>{ce.department_code}</Table.Cell>
              <Table.Cell>
                <span style={{ textTransform: "capitalize" }}>
                  {ce.status || "planned"}
                </span>
              </Table.Cell>
              <Table.Cell>{ce.budget_bac || "0.00"}</Table.Cell>
              <Table.Cell>{ce.revenue_plan || "0.00"}</Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
      <Flex justifyContent="flex-end" mt={4}>
        <PaginationRoot
          count={count}
          pageSize={PER_PAGE}
          onPageChange={({ page }) => setPage(page)}
        >
          <Flex>
            <PaginationPrevTrigger />
            <PaginationItems />
            <PaginationNextTrigger />
          </Flex>
        </PaginationRoot>
      </Flex>
    </>
  )
}

function WBEDetail() {
  const { id: projectId, wbeId } = Route.useParams()

  const { data: project, isLoading: isLoadingProject } = useQuery({
    ...getProjectQueryOptions({ id: projectId }),
  })

  const { data: wbe, isLoading: isLoadingWBE } = useQuery({
    ...getWBEQueryOptions({ id: wbeId }),
  })

  if (isLoadingProject || isLoadingWBE) {
    return (
      <Container maxW="full">
        <PendingItems />
      </Container>
    )
  }

  if (!project || !wbe) {
    return (
      <Container maxW="full">
        <EmptyState.Root>
          <EmptyState.Content>
            <EmptyState.Title>Project or WBE not found</EmptyState.Title>
          </EmptyState.Content>
        </EmptyState.Root>
      </Container>
    )
  }

  return (
    <Container maxW="full">
      <Flex alignItems="center" gap={2} pt={12} mb={2}>
        <Link
          to="/projects"
          color="blue.500"
          _hover={{ textDecoration: "underline" }}
        >
          <Text fontSize="sm">Projects</Text>
        </Link>
        <FiChevronRight />
        <Link
          to={`/projects/${project.project_id}`}
          color="blue.500"
          _hover={{ textDecoration: "underline" }}
        >
          <Text fontSize="sm">{project.project_name}</Text>
        </Link>
        <FiChevronRight />
        <Text fontSize="sm" color="gray.600">
          {wbe.machine_type}
        </Text>
      </Flex>
      <Heading size="lg">
        {project.project_name} - {wbe.machine_type}
      </Heading>
      <Box mt={4}>
        <Heading size="md" mb={4}>
          Cost Elements
        </Heading>
        <CostElementsTable wbeId={wbe.wbe_id} />
      </Box>
    </Container>
  )
}
