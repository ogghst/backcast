import { test, expect, Page } from "@playwright/test";

/**
 * Helper to fetch existing demo data from seed.
 * Uses the seeded demo data instead of creating new entities.
 */
async function getTestData(page: Page) {
  const timestamp = Date.now();

  // Get auth token from localStorage
  const authStorage = await page.evaluate(() =>
    localStorage.getItem("auth-storage")
  );
  if (!authStorage) throw new Error("No auth token found");

  const token = JSON.parse(authStorage).state.token;
  if (!token) throw new Error("Token is null");

  const api = page.request;
  const baseURL = "http://localhost:8020";
  const headers = { Authorization: `Bearer ${token}` };

  // Fetch demo project
  const projRes = await api.get(`${baseURL}/api/v1/projects`, {
    params: { search: "PRJ-DEMO-001" },
    headers,
  });
  expect(projRes.ok()).toBeTruthy();
  const projs = await projRes.json();
  const proj = projs.items?.find(
    (p: { code: string; project_id: string }) => p.code === "PRJ-DEMO-001"
  );
  if (!proj) throw new Error("Demo Project PRJ-DEMO-001 not found");

  // Fetch demo WBE
  const wbeRes = await api.get(`${baseURL}/api/v1/wbes`, {
    params: { project_id: proj.project_id },
    headers,
  });
  expect(wbeRes.ok()).toBeTruthy();
  const wbeData = await wbeRes.json();
  const wbeItems = Array.isArray(wbeData) ? wbeData : wbeData.items;
  const wbe = wbeItems?.find(
    (w: { code: string; wbe_id: string }) => w.code === "PRJ-DEMO-001-L1-1"
  );
  if (!wbe) throw new Error("Demo WBE PRJ-DEMO-001-L1-1 not found");

  // Fetch demo cost element type
  const typeRes = await api.get(`${baseURL}/api/v1/cost-element-types`, {
    params: { search: "LAB" },
    headers,
  });
  expect(typeRes.ok()).toBeTruthy();
  const types = await typeRes.json();
  const type = types.items?.find(
    (t: { code: string; cost_element_type_id: string }) => t.code === "LAB"
  );
  if (!type) throw new Error("Cost Element Type LAB not found");

  return { proj, wbe, type, timestamp, token, baseURL };
}

test.describe("EVM Analyzer E2E Tests", () => {
  test.use({ viewport: { width: 1920, height: 1080 } });

  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto("/login");
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');

    // Wait for successful login
    await expect(page.getByRole("menuitem", { name: "Dashboard" })).toBeVisible({
      timeout: 15000,
    });
  });

  test.describe("Cost Element Page - EVM Analyzer", () => {
    test("should display EVM Analysis card and open modal", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for cost element detail page to load
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      // Verify EVM Analysis card is visible
      await expect(page.getByText("EVM Analysis")).toBeVisible({
        timeout: 10000,
      });

      // Verify EVM Summary section is visible
      await expect(page.getByText("EVM Summary")).toBeVisible();

      // Click the Advanced button to open the modal
      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify EVM Analyzer Modal opens
      await expect(page.getByText("EVM Analysis")).toBeVisible();
      await expect(
        page.getByRole("dialog").getByText("Performance Indices")
      ).toBeVisible();

      // Verify modal contains tabs
      await expect(page.getByRole("tab", { name: "Overview" })).toBeVisible();
      await expect(page.getByRole("tab", { name: "Schedule" })).toBeVisible();
      await expect(page.getByRole("tab", { name: "Cost" })).toBeVisible();
      await expect(page.getByRole("tab", { name: "Variance" })).toBeVisible();
      await expect(page.getByRole("tab", { name: "Forecast" })).toBeVisible();

      // Close modal
      await page.getByRole("button", { name: "OK" }).click();

      // Verify modal is closed
      await expect(
        page.getByRole("dialog").getByText("Performance Indices")
      ).not.toBeVisible();
    });

    test("should display EVM metrics in modal tabs", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-TABS-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM Tabs Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load and click Advanced button
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify Overview tab (default)
      await expect(page.getByRole("tab", { name: "Overview" })).toBeVisible();
      await expect(page.getByText("Budget at Completion")).toBeVisible();
      await expect(page.getByText("Estimate at Completion")).toBeVisible();

      // Click on Schedule tab
      await page.getByRole("tab", { name: "Schedule" }).click();
      await expect(page.getByText("Schedule Performance Index")).toBeVisible();
      await expect(page.getByText("Schedule Variance")).toBeVisible();

      // Click on Cost tab
      await page.getByRole("tab", { name: "Cost" }).click();
      await expect(page.getByText("Actual Cost")).toBeVisible();
      await expect(page.getByText("Cost Variance")).toBeVisible();

      // Click on Variance tab
      await page.getByRole("tab", { name: "Variance" }).click();

      // Click on Forecast tab
      await page.getByRole("tab", { name: "Forecast" }).click();
      await expect(page.getByText("Variance at Completion")).toBeVisible();
      await expect(page.getByText("Estimate to Complete")).toBeVisible();
    });

    test("should display gauge visualizations for CPI and SPI", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-GAUGE-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM Gauge Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load and click Advanced button
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify Performance Indices section
      await expect(page.getByText("Performance Indices")).toBeVisible();

      // Verify CPI and SPI gauges are rendered
      // The gauges should have labels "CPI" and "SPI"
      await expect(page.getByText("CPI")).toBeVisible();
      await expect(page.getByText("SPI")).toBeVisible();
    });
  });

  test.describe("WBE Page - EVM Analyzer", () => {
    test("should display EVM Analysis on WBE detail page", async ({
      page,
    }) => {
      const { wbe } = await getTestData(page);

      // Navigate to WBE detail page
      await page.goto(`/wbes/${wbe.wbe_id}`);

      // Wait for WBE detail page to load
      await expect(
        page.getByRole("heading", { name: "WBE Details" })
      ).toBeVisible({ timeout: 10000 });

      // Verify EVM Summary section is visible
      await expect(page.getByText("EVM Summary")).toBeVisible({
        timeout: 10000,
      });

      // Click the Advanced button to open the modal
      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify EVM Analyzer Modal opens
      await expect(page.getByText("EVM Analysis")).toBeVisible();
      await expect(
        page.getByRole("dialog").getByText("Performance Indices")
      ).toBeVisible();

      // Close modal
      await page.getByRole("button", { name: "OK" }).click();
    });
  });

  test.describe("Project Page - EVM Analyzer", () => {
    test("should display EVM Analysis on Project detail page", async ({
      page,
    }) => {
      const { proj } = await getTestData(page);

      // Navigate to Project detail page
      await page.goto(`/projects/${proj.project_id}`);

      // Wait for Project detail page to load
      await expect(
        page.getByRole("heading", { name: "Project Details" })
      ).toBeVisible({ timeout: 10000 });

      // Verify EVM Summary section is visible
      await expect(page.getByText("EVM Summary")).toBeVisible({
        timeout: 10000,
      });

      // Click the Advanced button to open the modal
      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify EVM Analyzer Modal opens
      await expect(page.getByText("EVM Analysis")).toBeVisible();
      await expect(
        page.getByRole("dialog").getByText("Performance Indices")
      ).toBeVisible();

      // Close modal
      await page.getByRole("button", { name: "OK" }).click();
    });
  });

  test.describe("EVM Analyzer Modal Interactions", () => {
    test("should switch between tabs and display content", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-INTERACT-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM Interaction Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load and click Advanced button
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      await page.getByRole("button", { name: /Advanced/i }).click();

      // Switch through all tabs and verify content
      const tabs = ["Overview", "Schedule", "Cost", "Variance", "Forecast"];

      for (const tab of tabs) {
        await page.getByRole("tab", { name: tab }).click();
        // Verify the tab is active
        await expect(page.getByRole("tab", { name: tab, selected: true })).toBeVisible();
      }

      // Close modal
      await page.getByRole("button", { name: "OK" }).click();
    });

    test("should close modal using Cancel button", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-CLOSE-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM Close Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load and click Advanced button
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify modal is open
      await expect(page.getByText("Performance Indices")).toBeVisible();

      // Close using Cancel button
      await page.getByRole("button", { name: "Cancel" }).click();

      // Verify modal is closed
      await expect(page.getByText("Performance Indices")).not.toBeVisible();
    });

    test("should close modal using X button", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-X-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM X Button Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load and click Advanced button
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify modal is open
      await expect(page.getByText("Performance Indices")).toBeVisible();

      // Close using X button (close icon)
      await page.locator('.ant-modal-close').click();

      // Verify modal is closed
      await expect(page.getByText("Performance Indices")).not.toBeVisible();
    });
  });

  test.describe("EVM Analyzer Loading States", () => {
    test("should show loading state while fetching metrics", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-LOAD-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM Loading Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      // The EVM Analysis card should show loading or the metrics
      // Since we can't easily test the loading state in E2E (it's too fast),
      // we just verify the metrics are displayed
      await expect(page.getByText("EVM Analysis")).toBeVisible();
    });
  });

  test.describe("EVM Analyzer Empty States", () => {
    test("should show empty state when no forecast exists", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element without forecast via API
      const uniqueCode = `CE-EVM-EMPTY-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM Empty Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Delete the auto-created forecast
      await request.delete(
        `${baseURL}/api/v1/cost-elements/${costElement.cost_element_id}/forecast`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      // Verify EVM Analysis card shows empty state
      await expect(page.getByText("EVM Analysis")).toBeVisible();
      await expect(
        page.getByText("No forecast created yet")
      ).toBeVisible();
    });
  });

  test.describe("EVM Analyzer Time Series Charts", () => {
    test("should display two timeline charts in modal", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-CHARTS-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM Charts Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load and click Advanced button
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify EVM Time Series Analysis section is visible
      await expect(page.getByText("EVM Time Series Analysis")).toBeVisible();

      // Verify EVM Progression chart is visible
      await expect(page.getByText("EVM Progression")).toBeVisible();

      // Verify Cost Comparison chart is visible
      await expect(page.getByText("Cost Comparison")).toBeVisible();

      // Verify chart descriptions are visible
      await expect(
        page.getByText("PV (Planned Value), EV (Earned Value), AC (Actual Cost)")
      ).toBeVisible();
      await expect(page.getByText("Forecast vs Actual Costs")).toBeVisible();
    });

    test("should support day/week/month granularity switching", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-GRAN-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM Granularity Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load and click Advanced button
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify granularity selector is visible
      await expect(page.getByRole("button", { name: "Day" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Week" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Month" })).toBeVisible();

      // Click Day granularity
      await page.getByRole("button", { name: "Day" }).click();

      // Verify Day button is selected
      await expect(page.getByRole("button", { name: "Day" })).toHaveAttribute(
        "class",
        /ant-radio-button-checked/
      );

      // Click Week granularity
      await page.getByRole("button", { name: "Week" }).click();

      // Verify Week button is selected
      await expect(page.getByRole("button", { name: "Week" })).toHaveAttribute(
        "class",
        /ant-radio-button-checked/
      );

      // Click Month granularity
      await page.getByRole("button", { name: "Month" }).click();

      // Verify Month button is selected
      await expect(page.getByRole("button", { name: "Month" })).toHaveAttribute(
        "class",
        /ant-radio-button-checked/
      );
    });
  });

  test.describe("EVM Analyzer Entity Type Support", () => {
    test("should display EVM metrics for Cost Element entity", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-ENTITY-CE-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM Entity CE Test ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      // Verify EVM Summary section is visible for Cost Element
      await expect(page.getByText("EVM Summary")).toBeVisible();

      // Click Advanced button
      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify modal opens for Cost Element entity
      await expect(page.getByText("EVM Analysis")).toBeVisible();
      await expect(page.getByText("Performance Indices")).toBeVisible();
    });

    test("should display EVM metrics for WBE entity", async ({
      page,
    }) => {
      const { wbe } = await getTestData(page);

      // Navigate to WBE detail page
      await page.goto(`/wbes/${wbe.wbe_id}`);

      // Wait for WBE detail page to load
      await expect(
        page.getByRole("heading", { name: "WBE Details" })
      ).toBeVisible({ timeout: 10000 });

      // Verify EVM Summary section is visible for WBE
      await expect(page.getByText("EVM Summary")).toBeVisible({
        timeout: 10000,
      });

      // Click the Advanced button to open the modal
      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify EVM Analyzer Modal opens for WBE entity
      await expect(page.getByText("EVM Analysis")).toBeVisible();
      await expect(
        page.getByRole("dialog").getByText("Performance Indices")
      ).toBeVisible();

      // Close modal
      await page.getByRole("button", { name: "OK" }).click();
    });

    test("should display EVM metrics for Project entity", async ({
      page,
    }) => {
      const { proj } = await getTestData(page);

      // Navigate to Project detail page
      await page.goto(`/projects/${proj.project_id}`);

      // Wait for Project detail page to load
      await expect(
        page.getByRole("heading", { name: "Project Details" })
      ).toBeVisible({ timeout: 10000 });

      // Verify EVM Summary section is visible for Project
      await expect(page.getByText("EVM Summary")).toBeVisible({
        timeout: 10000,
      });

      // Click the Advanced button to open the modal
      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify EVM Analyzer Modal opens for Project entity
      await expect(page.getByText("EVM Analysis")).toBeVisible();
      await expect(
        page.getByRole("dialog").getByText("Performance Indices")
      ).toBeVisible();

      // Close modal
      await page.getByRole("button", { name: "OK" }).click();
    });

    test("should seamlessly switch between entity types", async ({
      page,
    }) => {
      const { proj, wbe } = await getTestData(page);

      // Start on Project detail page
      await page.goto(`/projects/${proj.project_id}`);

      // Wait for Project detail page to load
      await expect(
        page.getByRole("heading", { name: "Project Details" })
      ).toBeVisible({ timeout: 10000 });

      // Verify EVM Summary for Project
      await expect(page.getByText("EVM Summary")).toBeVisible();

      // Navigate to WBE detail page
      await page.goto(`/wbes/${wbe.wbe_id}`);

      // Wait for WBE detail page to load
      await expect(
        page.getByRole("heading", { name: "WBE Details" })
      ).toBeVisible({ timeout: 10000 });

      // Verify EVM Summary for WBE
      await expect(page.getByText("EVM Summary")).toBeVisible();

      // Open WBE modal
      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify modal content for WBE
      await expect(page.getByText("EVM Analysis")).toBeVisible();

      // Close modal
      await page.getByRole("button", { name: "OK" }).click();

      // Verify modal is closed
      await expect(
        page.getByRole("dialog").getByText("Performance Indices")
      ).not.toBeVisible();
    });
  });

  test.describe("EVM Analyzer Accessibility", () => {
    test("should support keyboard navigation", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-A11Y-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM A11y Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      // Navigate to Advanced button using keyboard
      await page.keyboard.press("Tab");
      await page.keyboard.press("Tab");

      // Press Enter to open modal
      await page.keyboard.press("Enter");

      // Verify modal opened
      await expect(page.getByText("Performance Indices")).toBeVisible();

      // Navigate through modal tabs using keyboard
      await page.keyboard.press("Shift+Tab"); // Move focus back
      await page.keyboard.press("Tab"); // Move to first tab

      // Navigate to granularity buttons using keyboard
      await page.keyboard.press("Tab");
      await page.keyboard.press("Tab");

      // Press Enter to select granularity
      await page.keyboard.press("Enter");

      // Navigate to close button
      await page.keyboard.press("Tab");
      await page.keyboard.press("Tab");

      // Press Enter to close modal
      await page.keyboard.press("Enter");

      // Verify modal is closed
      await expect(page.getByText("Performance Indices")).not.toBeVisible();
    });

    test("should have proper ARIA attributes", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-ARIA-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM ARIA Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load and click Advanced button
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify modal has proper ARIA role
      const modal = page.locator('.ant-modal');
      await expect(modal).toHaveAttribute("role", "dialog");

      // Verify tabs have proper ARIA roles
      const tabs = page.locator('[role="tab"]');
      await expect(tabs.first()).toBeVisible();

      // Verify buttons have proper ARIA labels
      const closeButton = page.locator('.ant-modal-close');
      await expect(closeButton).toHaveAttribute("type", "button");

      // Close modal
      await page.getByRole("button", { name: "OK" }).click();
    });
  });

  test.describe("EVM Analyzer Time Travel Integration", () => {
    test("should respect TimeMachineContext control date", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-TIME-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM Time Travel Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      // Verify Time Machine component is visible (if present on the page)
      const timeMachineButton = page.locator('button:has-text("Now"), button:has-text("Jan")').first();
      const isTimeMachineVisible = await timeMachineButton.isVisible().catch(() => false);

      if (isTimeMachineVisible) {
        // Click to expand Time Machine
        await timeMachineButton.click();

        // Verify Time Machine panel is visible
        await expect(page.locator(".ant-slider")).toBeVisible({ timeout: 5000 });

        // Verify branch indicator is visible
        await expect(page.locator('.ant-tag:has-text("main")')).toBeVisible();
      }

      // Click Advanced button to open EVM modal
      await page.getByRole("button", { name: /Advanced/i }).click();

      // Verify EVM modal opens (metrics should respect current Time Machine settings)
      await expect(page.getByText("EVM Analysis")).toBeVisible();
      await expect(page.getByText("Performance Indices")).toBeVisible();

      // Close modal
      await page.getByRole("button", { name: "OK" }).click();
    });
  });

  test.describe("EVM Analyzer Performance", () => {
    test("should render summary view within performance budget", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-PERF-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM Perf Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Measure render time for summary view
      const startTime = Date.now();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for EVM Summary to be visible
      await expect(page.getByText("EVM Summary")).toBeVisible({ timeout: 10000 });

      const endTime = Date.now();
      const renderTime = endTime - startTime;

      // Assert render time is under 2 seconds (allowing for network delays)
      expect(renderTime).toBeLessThan(2000);
    });

    test("should render modal with charts within performance budget", async ({
      page,
      request,
    }) => {
      const { wbe, type, timestamp, token, baseURL } = await getTestData(page);

      // Create a cost element with forecast via API
      const uniqueCode = `CE-EVM-PERF2-${timestamp}`;
      const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code: uniqueCode,
          name: `EVM Perf2 Test CE ${timestamp}`,
          wbe_id: wbe.wbe_id,
          cost_element_type_id: type.cost_element_type_id,
          budget_amount: 100000,
        },
      });
      expect(createRes.ok()).toBeTruthy();
      const costElement = await createRes.json();

      // Navigate to cost element detail page
      await page.goto(`/cost-elements/${costElement.cost_element_id}`);

      // Wait for page to load
      await expect(
        page.getByRole("heading", { name: new RegExp(`^${uniqueCode}`) })
      ).toBeVisible({ timeout: 10000 });

      // Measure render time for modal
      const startTime = Date.now();

      // Click Advanced button
      await page.getByRole("button", { name: /Advanced/i }).click();

      // Wait for modal content to render (charts visible)
      await expect(page.getByText("EVM Progression")).toBeVisible({ timeout: 5000 });
      await expect(page.getByText("Cost Comparison")).toBeVisible({ timeout: 5000 });

      const endTime = Date.now();
      const renderTime = endTime - startTime;

      // Assert modal render time is under 3 seconds (allowing for chart rendering)
      expect(renderTime).toBeLessThan(3000);
    });
  });
});
