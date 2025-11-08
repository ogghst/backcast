import { expect, test } from "@playwright/test"
import {
  ApiError,
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

const testEntities: {
  projectId?: string
  wbeId?: string
  costElementId?: string
} = {}

async function callApi<T>(label: string, fn: () => Promise<T>): Promise<T> {
  try {
    return await fn()
  } catch (error) {
    if (error instanceof ApiError) {
      console.error(`API error during ${label}:`, error.body)
    }
    throw error
  }
}

test.beforeAll(async () => {
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

  const me = await callApi("readUserMe", () => UsersService.readUserMe())

  const now = new Date()
  const today = now.toISOString().slice(0, 10)
  const nextMonth = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10)

  const project = await callApi("createProject", () =>
    ProjectsService.createProject({
      requestBody: {
        project_name: `E2E Project ${Date.now()}`,
        customer_name: "E2E Customer",
        start_date: today,
        planned_completion_date: nextMonth,
        project_manager_id: me.id,
        contract_value: 100000,
        status: "active",
        notes: "E2E setup for cost element tabs",
      },
    }),
  )

  const wbe = await callApi("createWbe", () =>
    WbesService.createWbe({
      requestBody: {
        machine_type: `Machine ${Date.now()}`,
        project_id: project.project_id,
        revenue_allocation: 50000,
        status: "active",
        notes: "E2E setup for cost element tabs",
      },
    }),
  )

  const costElementTypes = await callApi("readCostElementTypes", () =>
    CostElementTypesService.readCostElementTypes(),
  )
  const costElementTypeId = costElementTypes.data?.[0]?.cost_element_type_id

  if (!costElementTypeId) {
    throw new Error("No cost element type available for test setup")
  }

  const costElement = await callApi("createCostElement", () =>
    CostElementsService.createCostElement({
      requestBody: {
        department_code: `D-${Date.now()}`,
        department_name: "Quality Assurance",
        budget_bac: 10000,
        revenue_plan: 12000,
        status: "active",
        notes: "E2E setup for cost element tabs",
        wbe_id: wbe.wbe_id,
        cost_element_type_id: costElementTypeId,
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
        description: "Initial cost registration for Playwright test",
      },
    }),
  )

  await callApi("createEarnedValueEntry", () =>
    EarnedValueEntriesService.createEarnedValueEntry({
      requestBody: {
        cost_element_id: costElement.cost_element_id,
        completion_date: today,
        percent_complete: 25,
        earned_value: 2500,
        deliverables: "Initial deliverable",
        description: "Initial earned value entry for Playwright test",
      },
    }),
  )

  testEntities.projectId = project.project_id
  testEntities.wbeId = wbe.wbe_id
  testEntities.costElementId = costElement.cost_element_id
})

test("Earned Value tab displays the earned value entries table", async ({
  page,
}) => {
  const { projectId, wbeId, costElementId } = testEntities

  if (!projectId || !wbeId || !costElementId) {
    test.fail(true, "Test data was not initialized correctly")
    return
  }

  await page.goto(
    `/projects/${projectId}/wbes/${wbeId}/cost-elements/${costElementId}`,
  )

  await expect(
    page.getByRole("heading", { name: "Cost Registrations" }),
  ).toBeVisible()

  await page.getByRole("tab", { name: "Earned Value" }).click()

  await expect(page).toHaveURL(/view=earned-value/)

  await expect(
    page.getByRole("heading", { name: "Earned Value Entries" }),
  ).toBeVisible()

  await expect(
    page.getByRole("heading", { name: "Cost Registrations" }),
  ).toBeHidden()
})

test("Budget Summary tab displays the budget summary view", async ({
  page,
}) => {
  const { projectId, wbeId } = testEntities

  if (!projectId || !wbeId) {
    test.fail(true, "Test data was not initialized correctly")
    return
  }

  await page.goto(`/projects/${projectId}/wbes/${wbeId}`)

  await expect(
    page.getByRole("heading", { name: "Cost Elements" }),
  ).toBeVisible()

  await page.getByRole("tab", { name: "Budget Summary" }).click()

  await expect(page).toHaveURL(/tab=summary/)

  await expect(
    page.getByRole("heading", { name: "Budget Summary" }),
  ).toBeVisible()

  await expect(
    page.getByRole("heading", { name: "Cost Elements" }),
  ).toBeHidden()
})
