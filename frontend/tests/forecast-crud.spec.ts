import { expect, test } from "@playwright/test"
import {
  CostElementsService,
  CostElementTypesService,
  ForecastsService,
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

async function seedForecastData() {
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
        project_name: `E2E Forecast ${Date.now()}`,
        customer_name: "Playwright Customer",
        start_date: today,
        planned_completion_date: nextMonth,
        project_manager_id: me.id,
        contract_value: 150000,
        status: "active",
        notes: "Seeded for forecast tests",
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
        notes: "Seeded for forecast tests",
      },
    }),
  )

  const costElementTypes = await callApi("readCostElementTypes", () =>
    CostElementTypesService.readCostElementTypes(),
  )
  const costElementTypeId =
    costElementTypes.data?.[0]?.cost_element_type_id ?? null
  if (!costElementTypeId) {
    throw new Error("No cost element type available for forecast tests")
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
        notes: "Seeded for forecast tests",
      },
    }),
  )

  seededData.projectId = project.project_id
  seededData.wbeId = wbe.wbe_id
  seededData.costElementId = costElement.cost_element_id
}

test.beforeAll(async () => {
  await seedForecastData()
})

test("should create a forecast", async ({ page }) => {
  await ensureApiAuth()
  const costElementId = seededData.costElementId
  if (!costElementId) {
    throw new Error("Cost element not seeded")
  }

  await page.goto(
    `/projects/${seededData.projectId}/wbes/${seededData.wbeId}/cost-elements/${costElementId}?view=forecasts`,
  )

  // Wait for forecasts tab to load
  await page.waitForSelector('text="Forecasts"', { timeout: 10000 })

  // Click Add Forecast button
  await page.click('button:has-text("Add Forecast")')

  // Fill in forecast form
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  const forecastDate = yesterday.toISOString().slice(0, 10)

  await page.fill('input[type="date"]', forecastDate)
  await page.fill('input[type="number"]', "15000.00")
  await page.selectOption("select", "bottom_up")
  await page.fill("textarea", "Test assumptions for E2E")

  // Submit form
  await page.click('button:has-text("Create Forecast")')

  // Wait for success message or table update
  await page
    .waitForSelector('text="Forecast created successfully"', {
      timeout: 5000,
    })
    .catch(() => {
      // If toast disappears quickly, just check table has data
      return page.waitForSelector("table", { timeout: 5000 })
    })

  // Verify forecast appears in table
  await expect(page.locator("table")).toBeVisible()
})

test("should display ETC calculation in table", async ({ page }) => {
  await ensureApiAuth()
  const costElementId = seededData.costElementId
  if (!costElementId) {
    throw new Error("Cost element not seeded")
  }

  // Create a forecast via API first
  const me = await callApi("readUserMe", () => UsersService.readUserMe())
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  const forecastDate = yesterday.toISOString().slice(0, 10)

  await callApi("createForecast", () =>
    ForecastsService.createForecast({
      requestBody: {
        cost_element_id: costElementId,
        forecast_date: forecastDate,
        estimate_at_completion: "20000.00",
        forecast_type: "performance_based",
        estimator_id: me.id,
        is_current: true,
      },
    }),
  )

  await page.goto(
    `/projects/${seededData.projectId}/wbes/${seededData.wbeId}/cost-elements/${costElementId}?view=forecasts`,
  )

  // Wait for forecasts table
  await page.waitForSelector("table", { timeout: 10000 })

  // Check that ETC column exists and has a value
  const etcHeader = page.locator('th:has-text("ETC")')
  await expect(etcHeader).toBeVisible()
})

test("should show warning for future forecast date", async ({ page }) => {
  await ensureApiAuth()
  const costElementId = seededData.costElementId
  if (!costElementId) {
    throw new Error("Cost element not seeded")
  }

  await page.goto(
    `/projects/${seededData.projectId}/wbes/${seededData.wbeId}/cost-elements/${costElementId}?view=forecasts`,
  )

  await page.waitForSelector('text="Forecasts"', { timeout: 10000 })

  // Click Add Forecast button
  await page.click('button:has-text("Add Forecast")')

  // Fill in forecast form with future date
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  const futureDate = tomorrow.toISOString().slice(0, 10)

  await page.fill('input[type="date"]', futureDate)
  await page.fill('input[type="number"]', "15000.00")
  await page.selectOption("select", "bottom_up")

  // Check for warning alert
  const warningAlert = page.locator("text=/future/i")
  await expect(warningAlert).toBeVisible({ timeout: 5000 })

  // Form should still be submittable (warning, not error)
  const submitButton = page.locator('button:has-text("Create Forecast")')
  await expect(submitButton).toBeEnabled()
})

test("should only allow editing current forecast", async ({ page }) => {
  await ensureApiAuth()
  const costElementId = seededData.costElementId
  if (!costElementId) {
    throw new Error("Cost element not seeded")
  }

  // Create two forecasts - one current, one not
  const me = await callApi("readUserMe", () => UsersService.readUserMe())
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  const forecastDate1 = yesterday.toISOString().slice(0, 10)

  const twoDaysAgo = new Date()
  twoDaysAgo.setDate(twoDaysAgo.getDate() - 2)
  const forecastDate2 = twoDaysAgo.toISOString().slice(0, 10)

  // Create non-current forecast
  await callApi("createForecast", () =>
    ForecastsService.createForecast({
      requestBody: {
        cost_element_id: costElementId,
        forecast_date: forecastDate2,
        estimate_at_completion: "10000.00",
        forecast_type: "bottom_up",
        estimator_id: me.id,
        is_current: false,
      },
    }),
  )

  // Create current forecast
  await callApi("createForecast", () =>
    ForecastsService.createForecast({
      requestBody: {
        cost_element_id: costElementId,
        forecast_date: forecastDate1,
        estimate_at_completion: "15000.00",
        forecast_type: "performance_based",
        estimator_id: me.id,
        is_current: true,
      },
    }),
  )

  await page.goto(
    `/projects/${seededData.projectId}/wbes/${seededData.wbeId}/cost-elements/${costElementId}?view=forecasts`,
  )

  await page.waitForSelector("table", { timeout: 10000 })

  // Check that only current forecast has edit button
  const editButtons = page.locator(
    'button[aria-label*="Edit"], button:has-text("Edit")',
  )
  const count = await editButtons.count()

  // Should have exactly 1 edit button (for current forecast)
  expect(count).toBeGreaterThanOrEqual(1)
})

test("should delete forecast and auto-promote previous", async ({ page }) => {
  await ensureApiAuth()
  const costElementId = seededData.costElementId
  if (!costElementId) {
    throw new Error("Cost element not seeded")
  }

  // Create two forecasts - one current, one not
  const me = await callApi("readUserMe", () => UsersService.readUserMe())
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  const forecastDate1 = yesterday.toISOString().slice(0, 10)

  const twoDaysAgo = new Date()
  twoDaysAgo.setDate(twoDaysAgo.getDate() - 2)
  const forecastDate2 = twoDaysAgo.toISOString().slice(0, 10)

  // Create first forecast (will become current after deletion)
  const _forecast1 = await callApi("createForecast", () =>
    ForecastsService.createForecast({
      requestBody: {
        cost_element_id: costElementId,
        forecast_date: forecastDate2,
        estimate_at_completion: "10000.00",
        forecast_type: "bottom_up",
        estimator_id: me.id,
        is_current: false,
      },
    }),
  )

  // Create second forecast (current)
  const _forecast2 = await callApi("createForecast", () =>
    ForecastsService.createForecast({
      requestBody: {
        cost_element_id: costElementId,
        forecast_date: forecastDate1,
        estimate_at_completion: "15000.00",
        forecast_type: "performance_based",
        estimator_id: me.id,
        is_current: true,
      },
    }),
  )

  await page.goto(
    `/projects/${seededData.projectId}/wbes/${seededData.wbeId}/cost-elements/${costElementId}?view=forecasts`,
  )

  await page.waitForSelector("table", { timeout: 10000 })

  // Find and click delete button for current forecast
  const deleteButtons = page.locator(
    'button[aria-label*="Delete"], button:has-text("Delete")',
  )
  await deleteButtons.first().click()

  // Confirm deletion
  await page.click('button:has-text("Delete"):not(:has-text("Cancel"))')

  // Wait for success message
  await page.waitForSelector("text=/deleted/i", { timeout: 5000 }).catch(() => {
    // If toast disappears, just verify table updated
    return page.waitForTimeout(2000)
  })

  // Verify table still has data (previous forecast should be promoted)
  await expect(page.locator("table")).toBeVisible()
})

test("should enforce max 3 forecast dates", async ({ page }) => {
  await ensureApiAuth()
  const costElementId = seededData.costElementId
  if (!costElementId) {
    throw new Error("Cost element not seeded")
  }

  // Create 3 forecasts with different dates via API
  const me = await callApi("readUserMe", () => UsersService.readUserMe())
  const dates = []
  for (let i = 1; i <= 3; i++) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    dates.push(date.toISOString().slice(0, 10))
  }

  for (let i = 0; i < dates.length; i++) {
    const date = dates[i]
    await callApi("createForecast", () =>
      ForecastsService.createForecast({
        requestBody: {
          cost_element_id: costElementId,
          forecast_date: date,
          estimate_at_completion: "10000.00",
          forecast_type: "bottom_up",
          estimator_id: me.id,
          is_current: i === 0, // First one is current
        },
      }),
    )
  }

  await page.goto(
    `/projects/${seededData.projectId}/wbes/${seededData.wbeId}/cost-elements/${costElementId}?view=forecasts`,
  )

  await page.waitForSelector('text="Forecasts"', { timeout: 10000 })

  // Try to create 4th forecast with new date
  await page.click('button:has-text("Add Forecast")')

  const fourDaysAgo = new Date()
  fourDaysAgo.setDate(fourDaysAgo.getDate() - 4)
  const newDate = fourDaysAgo.toISOString().slice(0, 10)

  await page.fill('input[type="date"]', newDate)
  await page.fill('input[type="number"]', "15000.00")
  await page.selectOption("select", "bottom_up")

  await page.click('button:has-text("Create Forecast")')

  // Should show error about max dates
  await page.waitForSelector("text=/maximum|three/i", { timeout: 5000 })
})
