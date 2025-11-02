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
import { FiBox, FiChevronRight } from "react-icons/fi"
import { z } from "zod"

import { ProjectsService, WbesService } from "@/client"
import PendingItems from "@/components/Pending/PendingItems"
import {
  PaginationItems,
  PaginationNextTrigger,
  PaginationPrevTrigger,
  PaginationRoot,
} from "@/components/ui/pagination.tsx"

const projectDetailSearchSchema = z.object({
  page: z.number().catch(1),
})

const PER_PAGE = 10

function getProjectQueryOptions({ id }: { id: string }) {
  return {
    queryFn: () => ProjectsService.readProject({ id }),
    queryKey: ["projects", id],
  }
}

function getWBEsQueryOptions({
  projectId,
  page,
}: {
  projectId: string
  page: number
}) {
  return {
    queryFn: () =>
      WbesService.readWbes({
        projectId: projectId,
        skip: (page - 1) * PER_PAGE,
        limit: PER_PAGE,
      }),
    queryKey: ["wbes", { projectId: projectId, page }],
  }
}

export const Route = createFileRoute("/_layout/projects/$id")({
  component: ProjectDetail,
  validateSearch: (search) => projectDetailSearchSchema.parse(search),
})

function WBEsTable({ projectId }: { projectId: string }) {
  const navigate = useNavigate({ from: Route.fullPath })
  const { page } = Route.useSearch()

  const { data, isLoading, isPlaceholderData } = useQuery({
    ...getWBEsQueryOptions({ projectId, page }),
    placeholderData: (prevData) => prevData,
  })

  const setPage = (page: number) => {
    navigate({
      search: (prev) => ({ ...prev, page }),
    })
  }

  const wbes = data?.data.slice(0, PER_PAGE) ?? []
  const count = data?.count ?? 0

  if (isLoading) {
    return <PendingItems />
  }

  if (wbes.length === 0) {
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
    <>
      <Table.Root size={{ base: "sm", md: "md" }}>
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader w="md">Machine Type</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Status</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Serial Number</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Revenue Allocation</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Contracted Delivery</Table.ColumnHeader>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {wbes?.map((wbe) => (
            <Table.Row
              key={wbe.wbe_id}
              opacity={isPlaceholderData ? 0.5 : 1}
              cursor="pointer"
              onClick={() =>
                navigate({
                  to: `/projects/${projectId}/wbes/${wbe.wbe_id}`,
                  search: { page: 1 },
                })
              }
              _hover={{ bg: "gray.100" }}
            >
              <Table.Cell truncate maxW="md">
                {wbe.machine_type}
              </Table.Cell>
              <Table.Cell>
                <span style={{ textTransform: "capitalize" }}>
                  {wbe.status || "designing"}
                </span>
              </Table.Cell>
              <Table.Cell truncate maxW="sm">
                {wbe.serial_number || "N/A"}
              </Table.Cell>
              <Table.Cell>{wbe.revenue_allocation || "0.00"}</Table.Cell>
              <Table.Cell>
                {wbe.contracted_delivery_date
                  ? new Date(wbe.contracted_delivery_date).toLocaleDateString()
                  : "N/A"}
              </Table.Cell>
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

function ProjectDetail() {
  const { id } = Route.useParams()

  const { data: project, isLoading: isLoadingProject } = useQuery({
    ...getProjectQueryOptions({ id }),
  })

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
      <Box mt={4}>
        <Heading size="md" mb={4}>
          Work Breakdown Elements
        </Heading>
        <WBEsTable projectId={project.project_id} />
      </Box>
    </Container>
  )
}
