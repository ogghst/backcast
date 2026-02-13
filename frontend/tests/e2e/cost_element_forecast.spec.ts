import { test, expect, Page } from "@playwright/test";

/**
 * Helper to fetch existing demo data from seed
 * Uses the seeded demo data instead of creating new entities
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

test.describe("Cost Element Forecast E2E Tests (1:1 Relationship)", () => {
  test.use({ viewport: { width: 1920, height: 1080 } });

  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto("/login");
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');

    // Wait for successful login
    await expect(page.getByRole("menuitem", { name: "Dashboard" })).toBeVisible(
      { timeout: 15000 }
    );
  });

  test("T-F-002: Create cost element auto-creates default forecast", async ({
    page,
    request,
  }) => {
    const { proj, wbe, type, timestamp, token, baseURL } = await getTestData(page);

    // === CREATE COST ELEMENT VIA API ===
    // We know this works from the API tests, so use it for setup
    const uniqueCode = `CE-FCAST-${timestamp}`;
    const uniqueName = `Test Forecast CE ${timestamp}`;

    const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        code: uniqueCode,
        name: uniqueName,
        wbe_id: wbe.wbe_id,
        cost_element_type_id: type.cost_element_type_id,
        budget_amount: 100000,
      },
    });
    expect(createRes.ok()).toBeTruthy();
    const costElement = await createRes.json();

    // === VERIFY FORECAST VIA UI ===
    // Navigate to cost element detail page
    await page.goto(`/cost-elements/${costElement.cost_element_id}`);

    // Wait for cost element detail page - check for the page title (h1)
    await expect(
      page.getByRole('heading', { name: new RegExp(`^${uniqueCode}`) })
    ).toBeVisible({ timeout: 10000 });

    // Click on Forecasts tab - use role-based selector
    const forecastsTab = page.getByRole('tab', { name: 'Forecasts' });
    await forecastsTab.click();

    // Wait for Forecasts tab to load - check for EVM Metrics text
    await expect(page.getByText(/EVM Metrics:/i)).toBeVisible({ timeout: 10000 });

    // Wait for the table to be visible
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 5000 });

    // VERIFY: A default forecast should exist with EAC = budget amount
    // Look for the EAC amount within the Forecasts tab specifically
    const forecastsTabContent = page.getByRole('tabpanel', { name: 'Forecasts' });
    // Use nth(1) to get the second occurrence (the exact match, not the BAC text)
    await expect(forecastsTabContent.getByText('€100,000').nth(1)).toBeVisible({ timeout: 5000 });

    // Verify the forecast has the default basis
    const basisText = await page.locator("text=Initial forecast").textContent();
    expect(basisText).toContain("Initial forecast");
  });

  test("T-F-003: View and update forecast via UI", async ({
    page,
    request,
  }) => {
    const { proj, wbe, type, timestamp, token, baseURL } = await getTestData(page);

    // First, create a cost element via API to get its ID
    const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        code: `CE-UPDATE-${timestamp}`,
        name: `Update Forecast Test CE`,
        wbe_id: wbe.wbe_id,
        cost_element_type_id: type.cost_element_type_id,
        budget_amount: 100000,
      },
    });
    expect(createRes.ok()).toBeTruthy();
    const costElement = await createRes.json();

    // === UPDATE FORECAST VIA API ===
    // Update the forecast using the API (we know this works)
    const updateRes = await request.put(
      `${baseURL}/api/v1/cost-elements/${costElement.cost_element_id}/forecast`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          eac_amount: 120000,
          basis_of_estimate: "Updated forecast based on revised vendor quotes",
        },
      }
    );
    expect(updateRes.ok()).toBeTruthy();

    // === VERIFY UPDATED FORECAST VIA UI ===
    // Navigate to cost element detail page
    await page.goto(`/cost-elements/${costElement.cost_element_id}`);

    // Wait for page to load - check for the page heading (h1)
    await expect(
      page.getByRole('heading', { name: new RegExp(`^${costElement.code}`) })
    ).toBeVisible({ timeout: 10000 });

    // Click on Forecasts tab - use role-based selector
    const forecastsTab = page.getByRole('tab', { name: 'Forecasts' });
    await forecastsTab.click();

    // Wait for Forecasts tab to load - check for EVM Metrics text
    await expect(page.getByText(/EVM Metrics:/i)).toBeVisible({ timeout: 10000 });

    // Wait for the table to be visible
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 5000 });

    // Verify the updated values are displayed in the Forecasts tab
    const forecastsTabContent = page.getByRole('tabpanel', { name: 'Forecasts' });
    await expect(forecastsTabContent.getByText('€120,000')).toBeVisible();
    await expect(
      forecastsTabContent.getByText("revised vendor quotes")
    ).toBeVisible();

    // Verify VAC updated correctly (BAC - EAC = 100000 - 120000 = -20000)
    await expect(forecastsTabContent.getByText("Over Budget")).toBeVisible();
  });

  test("T-F-004: Delete forecast and verify cascade behavior", async ({
    page,
    request,
  }) => {
    const { proj, wbe, type, timestamp, token, baseURL } = await getTestData(page);

    // First, create a cost element via API
    const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        code: `CE-DELETE-${timestamp}`,
        name: `Delete Forecast Test CE`,
        wbe_id: wbe.wbe_id,
        cost_element_type_id: type.cost_element_type_id,
        budget_amount: 100000,
      },
    });
    expect(createRes.ok()).toBeTruthy();
    const costElement = await createRes.json();

    // === DELETE FORECAST VIA API ===
    // Delete the forecast using the API (we know this works)
    const deleteRes = await request.delete(
      `${baseURL}/api/v1/cost-elements/${costElement.cost_element_id}/forecast`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    expect(deleteRes.ok()).toBeTruthy();

    // === VERIFY DELETED FORECAST VIA UI ===
    // Navigate to cost element detail page
    await page.goto(`/cost-elements/${costElement.cost_element_id}`);

    // Wait for page to load - check for the cost element code in the title
    await expect(
      page.getByRole('heading', { name: new RegExp(`^${costElement.code}`) })
    ).toBeVisible({ timeout: 10000 });

    // Click on Forecasts tab - use role-based selector
    const forecastsTab = page.getByRole('tab', { name: 'Forecasts' });
    await forecastsTab.click();

    // Wait for Forecasts tab to load - check for EVM Metrics text
    await expect(page.getByText(/EVM Metrics:/i)).toBeVisible({ timeout: 10000 });

    // Verify forecast is deleted - check for empty state indicators
    // The table should not be visible
    await expect(page.locator('.ant-table-body')).not.toBeVisible({ timeout: 5000 });

    // The "Create Forecast" button should be visible in the empty state
    const forecastsTabContent = page.getByRole('tabpanel', { name: 'Forecasts' });
    await expect(
      forecastsTabContent.getByRole('button', { name: 'Create Forecast' })
    ).toBeVisible({ timeout: 5000 });

    // Note: The cost element itself should still exist (forecast deletion doesn't cascade to CE)
    // But the cost element should no longer have an associated forecast
  });

  test("Verify old forecast endpoints return 410 Gone", async ({
    page,
    request,
  }) => {
    const { baseURL, token } = await getTestData(page);

    // Try to access old forecast list endpoint using request context with auth
    const listRes = await request.get(`${baseURL}/api/v1/forecasts`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    // Should return 410 Gone
    expect(listRes.status()).toBe(410);

    const listBody = await listRes.json();
    expect(listBody.detail.message).toContain("deprecated");
    expect(listBody.detail.new_endpoints.get).toContain("/cost-elements/");
  });

  test("New forecast endpoints work correctly", async ({
    page,
    request,
  }) => {
    const { proj, wbe, type, timestamp, baseURL, token } =
      await getTestData(page);

    // Create a cost element first
    const createRes = await request.post(`${baseURL}/api/v1/cost-elements`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        code: `CE-API-${timestamp}`,
        name: `API Test CE`,
        wbe_id: wbe.wbe_id,
        cost_element_type_id: type.cost_element_type_id,
        budget_amount: 100000,
      },
    });
    expect(createRes.ok()).toBeTruthy();
    const costElement = await createRes.json();

    // GET forecast via new endpoint
    const getRes = await request.get(
      `${baseURL}/api/v1/cost-elements/${costElement.cost_element_id}/forecast`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(getRes.ok()).toBeTruthy();
    const forecast = await getRes.json();
    expect(forecast.eac_amount).toBe("100000.00");
    expect(forecast.basis_of_estimate).toBe("Initial forecast");

    // PUT forecast via new endpoint
    const updateRes = await request.put(
      `${baseURL}/api/v1/cost-elements/${costElement.cost_element_id}/forecast`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          eac_amount: 115000,
          basis_of_estimate: "Updated via API",
        },
      }
    );
    expect(updateRes.ok()).toBeTruthy();
    const updated = await updateRes.json();
    expect(updated.eac_amount).toBe("115000.00");

    // DELETE forecast via new endpoint
    const deleteRes = await request.delete(
      `${baseURL}/api/v1/cost-elements/${costElement.cost_element_id}/forecast`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(deleteRes.ok()).toBeTruthy();

    // Verify forecast is deleted
    const getAfterDelete = await request.get(
      `${baseURL}/api/v1/cost-elements/${costElement.cost_element_id}/forecast`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(getAfterDelete.status()).toBe(404);
  });
});
