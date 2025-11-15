import { expect, type Page, test } from "@playwright/test"

import {
  ApiError,
  LoginService,
  OpenAPI,
  ProjectsService,
  UsersService,
  WbesService,
} from "../src/client"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"

const testEntities: {
  projectId?: string
  wbeName?: string
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

async function loginThroughUi(page: Page) {
  await page.goto("/login")
  await page.getByPlaceholder("Email").fill(firstSuperuser)
  await page
    .getByPlaceholder("Password", { exact: true })
    .fill(firstSuperuserPassword)
  await page.getByRole("button", { name: "Log In" }).click()
  await page.waitForURL("/")
}

test.describe("Time machine control", () => {
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

    const today = new Date()
    const todayIso = today.toISOString().slice(0, 10)
    const completionDate = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000)
      .toISOString()
      .slice(0, 10)

    const project = await callApi("createProject", () =>
      ProjectsService.createProject({
        requestBody: {
          project_name: `Time Machine Project ${Date.now()}`,
          customer_name: "Playwright Customer",
          start_date: todayIso,
          planned_completion_date: completionDate,
          contract_value: 100000,
          status: "active",
          project_manager_id: me.id,
        },
      }),
    )

    const wbe = await callApi("createWbe", () =>
      WbesService.createWbe({
        requestBody: {
          project_id: project.project_id,
          machine_type: `Time Machine WBE ${Date.now()}`,
          revenue_allocation: 25000,
          status: "designing",
        },
      }),
    )

    testEntities.projectId = project.project_id
    testEntities.wbeName = wbe.machine_type
  })

  test("time machine control hides WBEs created after selected date", async ({
    page,
  }) => {
    if (!testEntities.projectId || !testEntities.wbeName) {
      test.fail(true, "Missing project or WBE test data")
      return
    }

    await loginThroughUi(page)

    await page.goto(`/projects/${testEntities.projectId}?tab=wbes&page=1`)
    await expect(page.getByText(testEntities.wbeName)).toBeVisible()

    const pastDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
      .toISOString()
      .slice(0, 10)

    const timeMachineInput = page.getByTestId("time-machine-input")
    await timeMachineInput.fill(pastDate)
    await timeMachineInput.blur()

    await expect(page.getByText("No WBEs found")).toBeVisible({
      timeout: 10000,
    })

    await page.getByTestId("time-machine-reset").click()

    await expect(page.getByText(testEntities.wbeName)).toBeVisible({
      timeout: 10000,
    })
  })
})
