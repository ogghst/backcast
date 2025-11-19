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
import { firstSuperuser, firstSuperuserPassword } from "./config"

interface SeededDashboardData {
  projectId?: string
  wbes: Array<{ id: string; name: string }>
}

const seededDashboardData: SeededDashboardData = {
  projectId: undefined,
  wbes: [],
}

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

async function seedProjectPerformanceDashboardData() {
  if (seededDashboardData.projectId) {
    return
  }

  await ensureApiAuth()
  const me = await callApi("readUserMe", () => UsersService.readUserMe())
  const today = new Date()
  const startDate = today.toISOString().slice(0, 10)
  const nextMonth = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10)

  const project = await callApi("createProject", () =>
    ProjectsService.createProject({
      requestBody: {
        project_name: `E2E Dashboard ${Date.now()}`,
        customer_name: "Playwright Customer",
        start_date: startDate,
        planned_completion_date: nextMonth,
        project_manager_id: me.id,
        contract_value: 250000,
        status: "active",
        notes: "Seeded for project performance dashboard tests",
      },
    }),
  )

  const wbeAlpha = await callApi("createWbeAlpha", () =>
    WbesService.createWbe({
      requestBody: {
        project_id: project.project_id,
        machine_type: "Alpha Drill",
        serial_number: `ALPHA-${Date.now()}`,
        revenue_allocation: 125000,
        status: "active",
        notes: "Seeded WBE Alpha",
      },
    }),
  )

  const wbeBeta = await callApi("createWbeBeta", () =>
    WbesService.createWbe({
      requestBody: {
        project_id: project.project_id,
        machine_type: "Beta Fabricator",
        serial_number: `BETA-${Date.now()}`,
        revenue_allocation: 125000,
        status: "active",
        notes: "Seeded WBE Beta",
      },
    }),
  )

  const costElementTypes = await callApi("readCostElementTypes", () =>
    CostElementTypesService.readCostElementTypes(),
  )
  const costElementTypeId =
    costElementTypes.data?.[0]?.cost_element_type_id ?? null
  if (!costElementTypeId) {
    throw new Error("No cost element type available for dashboard tests")
  }

  const alphaCostElement = await callApi("createAlphaCostElement", () =>
    CostElementsService.createCostElement({
      requestBody: {
        wbe_id: wbeAlpha.wbe_id,
        cost_element_type_id: costElementTypeId,
        department_code: "ALPHA",
        department_name: "Alpha Assembly",
        budget_bac: 80000,
        revenue_plan: 100000,
        status: "active",
        notes: "Alpha cost element for dashboard tests",
      },
    }),
  )

  const betaCostElement = await callApi("createBetaCostElement", () =>
    CostElementsService.createCostElement({
      requestBody: {
        wbe_id: wbeBeta.wbe_id,
        cost_element_type_id: costElementTypeId,
        department_code: "BETA",
        department_name: "Beta Fabrication",
        budget_bac: 70000,
        revenue_plan: 90000,
        status: "active",
        notes: "Beta cost element for dashboard tests",
      },
    }),
  )

  await callApi("createAlphaSchedule", () =>
    CostElementSchedulesService.createSchedule({
      costElementId: alphaCostElement.cost_element_id,
      requestBody: {
        start_date: startDate,
        end_date: nextMonth,
        progression_type: "linear",
        registration_date: startDate,
        description: "Alpha schedule",
      },
    }),
  )

  await callApi("createBetaSchedule", () =>
    CostElementSchedulesService.createSchedule({
      costElementId: betaCostElement.cost_element_id,
      requestBody: {
        start_date: startDate,
        end_date: nextMonth,
        progression_type: "linear",
        registration_date: startDate,
        description: "Beta schedule",
      },
    }),
  )

  await callApi("createAlphaCostRegistration", () =>
    CostRegistrationsService.createCostRegistration({
      requestBody: {
        cost_element_id: alphaCostElement.cost_element_id,
        registration_date: startDate,
        amount: 90000,
        cost_category: "labor",
        description: "Alpha overrun",
      },
    }),
  )

  await callApi("createBetaCostRegistration", () =>
    CostRegistrationsService.createCostRegistration({
      requestBody: {
        cost_element_id: betaCostElement.cost_element_id,
        registration_date: startDate,
        amount: 45000,
        cost_category: "material",
        description: "Beta spend",
      },
    }),
  )

  await callApi("createAlphaEV", () =>
    EarnedValueEntriesService.createEarnedValueEntry({
      requestBody: {
        cost_element_id: alphaCostElement.cost_element_id,
        completion_date: startDate,
        percent_complete: 55,
        description: "Alpha EV entry",
      },
    }),
  )

  await callApi("createBetaEV", () =>
    EarnedValueEntriesService.createEarnedValueEntry({
      requestBody: {
        cost_element_id: betaCostElement.cost_element_id,
        completion_date: startDate,
        percent_complete: 70,
        description: "Beta EV entry",
      },
    }),
  )

  seededDashboardData.projectId = project.project_id
  seededDashboardData.wbes = [
    { id: wbeAlpha.wbe_id, name: wbeAlpha.machine_type ?? "Alpha Drill" },
    { id: wbeBeta.wbe_id, name: wbeBeta.machine_type ?? "Beta Fabricator" },
  ]
}

test.beforeAll(async () => {
  await seedProjectPerformanceDashboardData()
})

test.describe("Project Performance Dashboard", () => {
  test("displays timeline, KPIs, filters, and drilldown navigation", async ({
    page,
  }) => {
    const projectId = seededDashboardData.projectId
    if (!projectId) {
      throw new Error("Dashboard seed data not initialized")
    }
    const [alphaWbe] = seededDashboardData.wbes

    await page.goto(`/projects/${projectId}?tab=metrics`)

    await page
      .getByRole("link", { name: /View Project Performance Dashboard/i })
      .click()

    await page.waitForURL(
      `/projects/${projectId}/reports/project-performance-dashboard`,
    )
    await expect(
      page.getByRole("heading", { name: "Project Performance Dashboard" }),
    ).toBeVisible()

    await expect(
      page.getByRole("heading", { name: "Timeline Overview" }),
    ).toBeVisible()
    await expect(page.getByText(/Loading timeline data/i)).not.toBeVisible({
      timeout: 5000,
    })

    await expect(
      page.getByRole("heading", { name: "Performance KPIs" }),
    ).toBeVisible()
    const kpiLabels = [
      "Cost Performance Index",
      "Schedule Performance Index",
      "To-Complete Performance Index",
      "Cost Variance",
      "Schedule Variance",
    ]
    for (const label of kpiLabels) {
      await expect(page.getByText(label, { exact: false })).toBeVisible()
    }

    if (alphaWbe) {
      const alphaCheckbox = page.getByRole("checkbox", {
        name: alphaWbe.name,
      })
      await alphaCheckbox.click()
      await expect(alphaCheckbox).toBeChecked()

      const clearFiltersButton = page.getByRole("button", {
        name: /Clear Filters/i,
      })
      await expect(clearFiltersButton).toBeEnabled()
      await clearFiltersButton.click()
      await expect(alphaCheckbox).not.toBeChecked()
    }

    await expect(
      page.getByRole("heading", { name: "Drilldown Focus" }),
    ).toBeVisible()
    await expect(page.getByText(/No variance issues found/i)).not.toBeVisible({
      timeout: 5000,
    })

    if (alphaWbe) {
      const wbeCell = page.getByRole("cell", { name: alphaWbe.name })
      await wbeCell.waitFor({ state: "visible" })
      await wbeCell.click()
      await page.waitForURL(`/projects/${projectId}/wbes/${alphaWbe.id}`)
      await expect(
        page.getByText(alphaWbe.name, { exact: false }),
      ).toBeVisible()
      await page.goBack()
      await page.waitForURL(
        `/projects/${projectId}/reports/project-performance-dashboard`,
      )
    }
  })
})
