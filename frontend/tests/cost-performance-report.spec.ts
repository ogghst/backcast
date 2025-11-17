import { expect, test } from "@playwright/test"
import {
  CostElementSchedulesService,
  CostElementsService,
  CostElementTypesService,
  CostRegistrationsService,
  EarnedValueEntriesService,
  LoginService,
  OpenAPI,
  ProjectsService,
  UsersService,
  WbesService,
} from "../src/client"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"

const seededData: {
  projectId?: string
  wbeId?: string
  costElementId?: string
} = {}

async function callApi<T>(label: string, fn: () => Promise<T>): Promise<T> {
  try {
    return await fn()
  } catch (error) {
    console.error(`API error during ${label}:`, error)
    throw error
  }
}

async function ensureApiAuth() {
  if (OpenAPI.TOKEN) {
    return
  }
  const apiBaseUrl = process.env.VITE_API_URL
  if (!apiBaseUrl) {
    throw new Error("VITE_API_URL is not defined")
  }
  OpenAPI.BASE = apiBaseUrl
  const token = await callApi("login", () =>
    LoginService.loginAccessToken({
      formData: {
        username: firstSuperuser,
        password: firstSuperuserPassword,
      },
    }),
  )
  OpenAPI.TOKEN = token.access_token
}

async function seedReportData() {
  await ensureApiAuth()
  const me = await callApi("readUserMe", () => UsersService.readUserMe())
  const now = new Date()
  const today = now.toISOString().slice(0, 10)
  const nextMonth = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10)

  const project = await callApi("createProject", () =>
    ProjectsService.createProject({
      requestBody: {
        project_name: `E2E Cost Report ${Date.now()}`,
        customer_name: "Playwright Customer",
        start_date: today,
        planned_completion_date: nextMonth,
        project_manager_id: me.id,
        contract_value: 150000,
        status: "active",
        notes: "Seeded for cost performance tests",
      },
    }),
  )

  const wbe = await callApi("createWbe", () =>
    WbesService.createWbe({
      requestBody: {
        project_id: project.project_id,
        machine_type: "Playwright Machine",
        serial_number: `PW-${Date.now()}`,
        revenue_allocation: 75000,
        status: "active",
        notes: "Seeded for cost performance tests",
      },
    }),
  )

  const costElementTypes = await callApi("readCostElementTypes", () =>
    CostElementTypesService.readCostElementTypes(),
  )
  const costElementTypeId =
    costElementTypes.data?.[0]?.cost_element_type_id ?? null
  if (!costElementTypeId) {
    throw new Error("No cost element type available for cost performance tests")
  }

  const costElement = await callApi("createCostElement", () =>
    CostElementsService.createCostElement({
      requestBody: {
        wbe_id: wbe.wbe_id,
        cost_element_type_id: costElementTypeId,
        department_code: "QA",
        department_name: "Quality Assurance",
        budget_bac: 10000,
        revenue_plan: 12000,
        status: "active",
        notes: "Seeded for cost performance tests",
      },
    }),
  )

  await callApi("createCostElementSchedule", () =>
    CostElementSchedulesService.createSchedule({
      costElementId: costElement.cost_element_id,
      requestBody: {
        start_date: today,
        end_date: nextMonth,
        progression_type: "linear",
        registration_date: today,
        description: "Initial schedule for cost performance tests",
      },
    }),
  )

  await callApi("createCostRegistration", () =>
    CostRegistrationsService.createCostRegistration({
      requestBody: {
        cost_element_id: costElement.cost_element_id,
        registration_date: today,
        amount: 5000,
        cost_category: "labor",
        description: "Seeded cost registration",
      },
    }),
  )

  await callApi("createEarnedValueEntry", () =>
    EarnedValueEntriesService.createEarnedValueEntry({
      requestBody: {
        cost_element_id: costElement.cost_element_id,
        completion_date: today,
        percent_complete: 50,
        description: "Seeded EV entry",
      },
    }),
  )

  seededData.projectId = project.project_id
  seededData.wbeId = wbe.wbe_id
  seededData.costElementId = costElement.cost_element_id
}

async function createEmptyProject() {
  await ensureApiAuth()
  const me = await callApi("readUserMe", () => UsersService.readUserMe())
  const today = new Date().toISOString().slice(0, 10)
  const nextMonth = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10)
  const project = await callApi("createEmptyProject", () =>
    ProjectsService.createProject({
      requestBody: {
        project_name: `Empty Cost Report ${Date.now()}`,
        customer_name: "Playwright Customer",
        start_date: today,
        planned_completion_date: nextMonth,
        project_manager_id: me.id,
        contract_value: 50000,
        status: "active",
        notes: "Empty project for cost performance tests",
      },
    }),
  )
  return project.project_id
}

test.beforeAll(async () => {
  await seedReportData()
})

test.describe("Cost Performance Report", () => {
  test("should navigate to cost performance report from project metrics tab", async ({
    page,
  }) => {
    if (!seededData.projectId) {
      throw new Error("Seed data not initialized")
    }
    await page.goto(`/projects/${seededData.projectId}?tab=metrics`)

    await page
      .getByRole("link", { name: /View Cost Performance Report/i })
      .click()

    // Wait for report page to load
    await page.waitForURL(/\/projects\/[^/]+\/reports\/cost-performance/)

    // Verify report is displayed
    await expect(
      page.getByRole("heading", { name: "Cost Performance Report" }),
    ).toBeVisible()
  })

  test("should display report data in table", async ({ page }) => {
    if (!seededData.projectId) {
      throw new Error("Seed data not initialized")
    }
    await page.goto(
      `/projects/${seededData.projectId}/reports/cost-performance`,
    )

    // Wait for report to load
    await page
      .getByRole("heading", { name: "Cost Performance Report" })
      .waitFor({ state: "visible" })

    // Verify table is present (may be empty)
    const table = page.locator("table").first()
    await expect(table).toBeVisible()

    // Verify summary section is present
    await expect(page.locator("text=Project Summary")).toBeVisible()
  })

  test("should handle empty report gracefully", async ({ page }) => {
    const emptyProjectId = await createEmptyProject()
    await page.goto(`/projects/${emptyProjectId}/reports/cost-performance`)

    // Verify empty state message
    await expect(
      page.locator("text=No cost elements found for this project"),
    ).toBeVisible()
  })
})
