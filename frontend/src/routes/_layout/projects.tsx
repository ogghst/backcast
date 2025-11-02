import {
  Container,
  EmptyState,
  Flex,
  Heading,
  Table,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import {
  createFileRoute,
  Outlet,
  useNavigate,
  useRouterState,
} from "@tanstack/react-router"
import { FiFolder } from "react-icons/fi"
import { z } from "zod"

import { ProjectsService } from "@/client"
import PendingItems from "@/components/Pending/PendingItems"
import AddProject from "@/components/Projects/AddProject"
import {
  PaginationItems,
  PaginationNextTrigger,
  PaginationPrevTrigger,
  PaginationRoot,
} from "@/components/ui/pagination.tsx"

const projectsSearchSchema = z.object({
  page: z.number().catch(1),
})

const PER_PAGE = 10

function getProjectsQueryOptions({ page }: { page: number }) {
  return {
    queryFn: () =>
      ProjectsService.readProjects({
        skip: (page - 1) * PER_PAGE,
        limit: PER_PAGE,
      }),
    queryKey: ["projects", { page }],
  }
}

export const Route = createFileRoute("/_layout/projects")({
  component: Projects,
  validateSearch: (search) => projectsSearchSchema.parse(search),
})

function ProjectsTable() {
  const navigate = useNavigate({ from: Route.fullPath })
  const { page } = Route.useSearch()

  const { data, isLoading, isPlaceholderData } = useQuery({
    ...getProjectsQueryOptions({ page }),
    placeholderData: (prevData) => prevData,
  })

  const setPage = (page: number) => {
    navigate({
      to: "/projects",
      search: (prev) => ({ ...prev, page }),
    })
  }

  const projects = data?.data.slice(0, PER_PAGE) ?? []
  const count = data?.count ?? 0

  if (isLoading) {
    return <PendingItems />
  }

  if (projects.length === 0) {
    return (
      <EmptyState.Root>
        <EmptyState.Content>
          <EmptyState.Indicator>
            <FiFolder />
          </EmptyState.Indicator>
          <VStack textAlign="center">
            <EmptyState.Title>No projects found</EmptyState.Title>
            <EmptyState.Description>
              Create a new project to get started
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
            <Table.ColumnHeader w="md">Project Name</Table.ColumnHeader>
            <Table.ColumnHeader w="md">Customer</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Status</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Start Date</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Planned Completion</Table.ColumnHeader>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {projects?.map((project) => (
            <Table.Row
              key={project.project_id}
              opacity={isPlaceholderData ? 0.5 : 1}
              cursor="pointer"
              onClick={() => {
                navigate({
                  to: "/projects/$id",
                  params: { id: project.project_id },
                  search: { page: 1 },
                })
              }}
              _hover={{ bg: "gray.100" }}
            >
              <Table.Cell truncate maxW="md">
                {project.project_name}
              </Table.Cell>
              <Table.Cell truncate maxW="md">
                {project.customer_name}
              </Table.Cell>
              <Table.Cell>
                <span style={{ textTransform: "capitalize" }}>
                  {project.status || "active"}
                </span>
              </Table.Cell>
              <Table.Cell>
                {new Date(project.start_date).toLocaleDateString()}
              </Table.Cell>
              <Table.Cell>
                {new Date(project.planned_completion_date).toLocaleDateString()}
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

function Projects() {
  // In TanStack Router, when child routes exist, we need to render Outlet
  // Check if we're on exact /projects route (no child route)
  const location = useRouterState({
    select: (state) => state.location.pathname,
  })
  const isExactProjectsRoute = location === "/projects"

  return (
    <>
      {isExactProjectsRoute && (
        <Container maxW="full">
          <Heading size="lg" pt={12}>
            Projects Management
          </Heading>
          <AddProject />
          <ProjectsTable />
        </Container>
      )}
      <Outlet />
    </>
  )
}
