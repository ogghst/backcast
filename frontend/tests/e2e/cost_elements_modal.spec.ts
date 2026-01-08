import { test, expect, Page } from "@playwright/test";

/**
 * Isolated test for Cost Element Modal Type Selection
 * Focuses specifically on the type dropdown functionality
 */

async function seedMinimalData(page: Page) {
  const timestamp = Date.now();

  const authStorage = await page.evaluate(() =>
    localStorage.getItem("auth-storage")
  );
  const token = JSON.parse(authStorage!).state.token;
  const api = page.request;
  const baseURL = "http://localhost:8020";
  const headers = { Authorization: `Bearer ${token}` };

  // Create department
  const deptRes = await api.post(`${baseURL}/api/v1/departments`, {
    data: { name: `Dept ${timestamp}`, code: `D${timestamp}` },
    headers,
  });
  const dept = await deptRes.json();

  // Create type
  const typeRes = await api.post(`${baseURL}/api/v1/cost-element-types`, {
    data: {
      name: `Type ${timestamp}`,
      code: `T${timestamp}`,
      department_id: dept.department_id,
    },
    headers,
  });
  const type = await typeRes.json();

  // Create project
  const projRes = await api.post(`${baseURL}/api/v1/projects`, {
    data: {
      name: `Proj ${timestamp}`,
      code: `P${timestamp}`,
      budget: 100000,
    },
    headers,
  });
  const proj = await projRes.json();

  // Create WBE
  const wbeRes = await api.post(`${baseURL}/api/v1/wbes`, {
    data: {
      project_id: proj.project_id,
      name: `WBE ${timestamp}`,
      code: "1.0",
      budget_allocation: 100000,
    },
    headers,
  });
  const wbe = await wbeRes.json();

  return { dept, type, proj, wbe, timestamp };
}

test.describe("Cost Element Modal - Type Selection", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');
    await expect(page.getByRole("menuitem", { name: "Dashboard" })).toBeVisible(
      {
        timeout: 30000,
      }
    );
  });

  test("should populate type dropdown when modal opens", async ({ page }) => {
    test.setTimeout(60000);

    const { proj, wbe, type } = await seedMinimalData(page);

    // Navigate to WBE detail page
    await page.goto(`/projects/${proj.project_id}/wbes/${wbe.wbe_id}`);
    await expect(
      page.getByRole("heading", { name: "WBE Details" })
    ).toBeVisible({
      timeout: 15000,
    });

    // Open the Add Cost Element modal
    await page.waitForTimeout(500);
    await page.click('button:has-text("Add Cost Element")');

    // Wait for modal to be visible
    await expect(page.locator(".ant-modal-body").last()).toBeVisible({
      timeout: 10000,
    });

    // Wait a bit for the options to load
    await page.waitForTimeout(2000);

    // Click on the Type select to open dropdown
    await page.click('input[id="cost_element_form_cost_element_type_id"]');

    // Wait for dropdown to be visible
    await expect(page.locator(".ant-select-dropdown")).toBeVisible({
      timeout: 5000,
    });

    // Check if our created type appears in the dropdown
    const typeOption = page.locator(
      `.ant-select-item-option-content:has-text("${type.code}")`
    );

    // Log all available options for debugging
    const allOptions = await page
      .locator(".ant-select-item-option-content")
      .allInnerTexts();
    console.log(
      `Found ${allOptions.length} type options in dropdown:`,
      allOptions.slice(0, 5)
    );

    // Verify our type is in the dropdown
    await expect(typeOption.first()).toBeVisible({ timeout: 10000 });

    console.log(`✓ Successfully found type ${type.code} in dropdown`);
  });

  test("should create cost element with selected type", async ({ page }) => {
    test.setTimeout(60000);

    const { proj, wbe, type } = await seedMinimalData(page);

    // Navigate to WBE detail page
    await page.goto(`/projects/${proj.project_id}/wbes/${wbe.wbe_id}`);
    await expect(
      page.getByRole("heading", { name: "WBE Details" })
    ).toBeVisible({
      timeout: 15000,
    });

    // Open modal
    await page.waitForTimeout(500);
    await page.click('button:has-text("Add Cost Element")');
    await expect(page.locator(".ant-modal-body").last()).toBeVisible();

    // Fill in basic fields
    const elementName = `CE ${Date.now()}`;
    const elementCode = `CE${Date.now()}`.substring(0, 10);

    await page.fill('input[id="cost_element_form_name"]', elementName);
    await page.fill('input[id="cost_element_form_code"]', elementCode);
    await page.locator("#cost_element_form_budget_amount").fill("5000");

    // Select the type
    await page.click('input[id="cost_element_form_cost_element_type_id"]');
    await expect(page.locator(".ant-select-dropdown")).toBeVisible();

    // Wait a bit for options to render
    await page.waitForTimeout(1000);

    const typeOption = page
      .locator(`.ant-select-item-option-content:has-text("${type.code}")`)
      .first();

    await expect(typeOption).toBeVisible({ timeout: 10000 });
    await typeOption.click();

    // Submit the form
    await page.click('button:has-text("Create")');

    // Verify the cost element appears in the list
    await expect(page.locator(`text=${elementCode}`)).toBeVisible({
      timeout: 15000,
    });

    console.log(
      `✓ Successfully created cost element ${elementCode} with type ${type.code}`
    );
  });
});
