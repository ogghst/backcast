import { expect, test } from "@playwright/test"
import {
  ApiError,
  BaselineLogsService,
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

const testEntities: {
  projectId?: string
  wbeId?: string
  costElementId?: string
  baselineId?: string
  latestScheduleRegistrationDate?: string
  previousScheduleRegistrationDate?: string
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
  const secondMonth = new Date(now.getTime() + 60 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10)
  const secondRegistrationDate = new Date(
    now.getTime() + 7 * 24 * 60 * 60 * 1000,
  )
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

  await callApi("createCostElementSchedule", () =>
    CostElementSchedulesService.createSchedule({
      costElementId: costElement.cost_element_id,
      requestBody: {
        start_date: today,
        end_date: nextMonth,
        progression_type: "linear",
        notes: "Timeline schedule for Playwright test",
        registration_date: today,
        description: "Initial schedule registration",
      },
    }),
  )

  await callApi("createCostElementSchedule", () =>
    CostElementSchedulesService.createSchedule({
      costElementId: costElement.cost_element_id,
      requestBody: {
        start_date: secondRegistrationDate,
        end_date: secondMonth,
        progression_type: "gaussian",
        notes: "Updated schedule for Playwright test",
        registration_date: secondRegistrationDate,
        description: "Second schedule registration",
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

  const baseline = await callApi("createBaselineLog", () =>
    BaselineLogsService.createBaselineLog({
      projectId: project.project_id,
      requestBody: {
        baseline_type: "earned_value",
        baseline_date: today,
        milestone_type: "commissioning_start",
        description: "Baseline for Playwright E2E",
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
  testEntities.baselineId = baseline.baseline_id
  testEntities.previousScheduleRegistrationDate = today
  testEntities.latestScheduleRegistrationDate = secondRegistrationDate
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

test("Baseline modal shows earned value tab with baseline entries", async ({
  page,
}) => {
  const { projectId, baselineId } = testEntities

  if (!projectId || !baselineId) {
    test.fail(true, "Baseline test data was not initialized correctly")
    return
  }

  await page.goto(`/projects/${projectId}?tab=baselines`)

  await page.getByRole("button", { name: "View baseline" }).first().click()

  await expect(page.getByText("Total Planned Value")).toBeVisible()

  await expect(page.getByRole("tab", { name: "Earned Value" })).toBeVisible()

  await page.getByRole("tab", { name: "Earned Value" }).click()

  await expect(
    page.getByRole("heading", { name: "Earned Value Snapshot" }),
  ).toBeVisible()

  await expect(page.getByRole("cell", { name: "25.00%" })).toBeVisible()

  await page.keyboard.press("Escape")
})

test("Edit cost element modal exposes schedule registration metadata", async ({
  page,
}) => {
  const { projectId, wbeId, costElementId } = testEntities

  if (!projectId || !wbeId || !costElementId) {
    test.fail(
      true,
      "Cost element schedule test data was not initialized correctly",
    )
    return
  }

  await page.goto(
    `/projects/${projectId}/wbes/${wbeId}/cost-elements/${costElementId}`,
  )

  await page.getByRole("button", { name: "Edit cost element" }).first().click()

  await expect(page.getByLabel("Registration Date")).toBeVisible()
  await expect(page.getByLabel("Registration Date")).toHaveValue(
    testEntities.latestScheduleRegistrationDate,
  )
  await expect(page.getByLabel("Schedule Description")).toHaveValue(
    "Second schedule registration",
  )

  await page.getByRole("button", { name: "Cancel" }).click()
})

test("Edit cost element modal shows schedule history entries", async ({
  page,
}) => {
  const { projectId, wbeId, costElementId, latestScheduleRegistrationDate } =
    testEntities

  if (
    !projectId ||
    !wbeId ||
    !costElementId ||
    !latestScheduleRegistrationDate
  ) {
    test.fail(true, "Schedule history test data was not initialized correctly")
    return
  }

  await page.goto(
    `/projects/${projectId}/wbes/${wbeId}/cost-elements/${costElementId}`,
  )

  await page.getByRole("button", { name: "Edit cost element" }).first().click()

  const historyRows = page.locator('[data-testid="schedule-history-row"]')
  await expect(historyRows).toHaveCount(2)
  await expect(historyRows.first()).toContainText(
    `${latestScheduleRegistrationDate}`,
  )
  await expect(historyRows.first()).toContainText(
    "Second schedule registration",
  )
  await expect(historyRows.nth(1)).toContainText(
    "Initial schedule registration",
  )

  await page.getByRole("button", { name: "Cancel" }).click()
})

test("Metrics tab displays combined budget and cost summaries", async ({
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

  await page.getByRole("tab", { name: "Metrics" }).click()

  await expect(page).toHaveURL(/tab=metrics/)

  await expect(
    page.getByRole("heading", { name: "Budget Summary" }),
  ).toBeVisible()

  await expect(
    page.getByRole("heading", { name: "Cost Summary" }),
  ).toBeVisible()
})

test("Old tab=summary silently maps to Metrics content (no redirect)", async ({
  page,
}) => {
  const { projectId, wbeId } = testEntities
  if (!projectId || !wbeId) {
    test.fail(true, "Test data was not initialized correctly")
    return
  }
  await page.goto(`/projects/${projectId}/wbes/${wbeId}?tab=summary`)
  // URL remains with summary (silent mapping)
  await expect(page).toHaveURL(/tab=summary/)
  // Metrics content is shown
  await expect(
    page.getByRole("heading", { name: "Budget Summary" }),
  ).toBeVisible()
  await expect(
    page.getByRole("heading", { name: "Cost Summary" }),
  ).toBeVisible()
})

test("Old tab=cost-summary silently maps to Metrics content (no redirect)", async ({
  page,
}) => {
  const { projectId, wbeId } = testEntities
  if (!projectId || !wbeId) {
    test.fail(true, "Test data was not initialized correctly")
    return
  }
  await page.goto(`/projects/${projectId}/wbes/${wbeId}?tab=cost-summary`)
  // URL remains with cost-summary (silent mapping)
  await expect(page).toHaveURL(/tab=cost-summary/)
  // Metrics content is shown
  await expect(
    page.getByRole("heading", { name: "Budget Summary" }),
  ).toBeVisible()
  await expect(
    page.getByRole("heading", { name: "Cost Summary" }),
  ).toBeVisible()
})

test("Budget timeline shows earned value dataset with collapsible filters", async ({
  page,
}) => {
  const { projectId } = testEntities

  if (!projectId) {
    test.fail(true, "Project test data was not initialized correctly")
    return
  }

  await page.goto(`/projects/${projectId}/budget-timeline`)

  await expect(
    page.getByRole("heading", { name: "Filter Budget Timeline" }),
  ).toBeVisible()

  await expect(page.getByText("Select WBEs to include")).not.toBeVisible()

  await page.getByRole("button", { name: "WBEs" }).click()

  await expect(
    page.getByRole("button", { name: "Select All" }).first(),
  ).toBeVisible()

  await expect(page.getByText("Earned Value (EV)")).toBeVisible()
  await expect(page.getByText("Planned Value (PV)")).toBeVisible()
})
