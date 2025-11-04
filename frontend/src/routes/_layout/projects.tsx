import { Container, EmptyState, Flex, Heading, VStack } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import {
  createFileRoute,
  Outlet,
  useNavigate,
  useRouterState,
} from "@tanstack/react-router"
import { FiFolder } from "react-icons/fi"
import { z } from "zod"
import type { ProjectPublic } from "@/client"
import { ProjectsService } from "@/client"
import { DataTable } from "@/components/DataTable/DataTable"
import type { ColumnDefExtended } from "@/components/DataTable/types"
import AddProject from "@/components/Projects/AddProject"
import DeleteProject from "@/components/Projects/DeleteProject"
import EditProject from "@/components/Projects/EditProject"

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

// Column definitions for Projects table
const projectsColumns: ColumnDefExtended<ProjectPublic>[] = [
  {
    accessorKey: "project_name",
    header: "Project Name",
    enableSorting: true,
    enableResizing: true,
    enableColumnFilter: true,
    filterType: "text",
    size: 250,
    defaultVisible: true,
  },
  {
    accessorKey: "customer_name",
    header: "Customer",
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
      options: ["active", "on-hold", "completed", "cancelled"],
    },
    size: 120,
    defaultVisible: true,
    cell: ({ getValue }) => (
      <span style={{ textTransform: "capitalize" }}>
        {(getValue() as string) || "active"}
      </span>
    ),
  },
  {
    accessorKey: "start_date",
    header: "Start Date",
    enableSorting: true,
    enableResizing: true,
    size: 120,
    defaultVisible: true,
    cell: ({ getValue }) => new Date(getValue() as string).toLocaleDateString(),
  },
  {
    accessorKey: "planned_completion_date",
    header: "Planned Completion",
    enableSorting: true,
    enableResizing: true,
    size: 150,
    defaultVisible: true,
    cell: ({ getValue }) => new Date(getValue() as string).toLocaleDateString(),
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
        <EditProject project={row.original} />
        <DeleteProject
          id={row.original.project_id}
          projectName={row.original.project_name}
        />
      </Flex>
    ),
  },
]

function ProjectsTable() {
  const navigate = useNavigate({ from: Route.fullPath })
  const { page } = Route.useSearch()

  const { data, isLoading } = useQuery({
    ...getProjectsQueryOptions({ page }),
    placeholderData: (prevData) => prevData,
  })

  const setPage = (page: number) => {
    navigate({
      to: "/projects",
      search: (prev) => ({ ...prev, page }),
    })
  }

  const projects = data?.data ?? []
  const count = data?.count ?? 0

  const handleRowClick = (project: ProjectPublic) => {
    navigate({
      to: "/projects/$id",
      params: { id: project.project_id },
      search: { page: 1 },
    })
  }

  if (!isLoading && projects.length === 0) {
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
    <DataTable
      data={projects}
      columns={projectsColumns}
      tableId="projects-table"
      onRowClick={handleRowClick}
      isLoading={isLoading}
      count={count}
      page={page}
      onPageChange={setPage}
      pageSize={PER_PAGE}
    />
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
