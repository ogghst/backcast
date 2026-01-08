import { test, expect, Page } from "@playwright/test";

/**
 * Simplified Cost Element Modal Test
 * Tests that dropdowns populate and cost element creation works
 * Uses existing data from the database instead of creating new test data
 */

test.describe("Cost Element Modal - Basic Functionality", () => {
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

  test("should load existing project and WBE", async ({ page, request }) => {
    // Get auth token
    const authStorage = await page.evaluate(() =>
      localStorage.getItem("auth-storage")
    );
    const token = JSON.parse(authStorage!).state.token;

    // Fetch an existing project with WBEs
    const projResponse = await request.get(
      "http://localhost:8020/api/v1/projects?page=1&per_page=10",
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    const projData = await projResponse.json();
    expect(projData.items.length).toBeGreaterThan(0);

    const project = projData.items[0];
    console.log(`Using project: ${project.code} - ${project.name}`);

    // Fetch WBEs for this project
    const wbeResponse = await request.get(
      `http://localhost:8020/api/v1/wbes?project_id=${project.project_id}&branch=main`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    const wbes = await wbeResponse.json();
    const wbeList = Array.isArray(wbes) ? wbes : wbes.items || [];
    expect(wbeList.length).toBeGreaterThan(0);

    const wbe = wbeList[0];
    console.log(`Using WBE: ${wbe.code} - ${wbe.name}`);

    // Navigate to the WBE detail page
    await page.goto(`/projects/${project.project_id}/wbes/${wbe.wbe_id}`);
    await expect(
      page.getByRole("heading", { name: "WBE Details" })
    ).toBeVisible({
      timeout: 15000,
    });

    // Open the Add Cost Element modal
    await page.waitForTimeout(500);
    await page.click('button:has-text("Add Cost Element")');

    // Wait for modal
    await expect(page.locator(".ant-modal-body").last()).toBeVisible({
      timeout: 10000,
    });

    // Wait for options to load
    await page.waitForTimeout(2000);

    // Click on the Type select to open dropdown
    await page.click('input[id="cost_element_form_cost_element_type_id"]');

    // Wait for dropdown
    await expect(page.locator(".ant-select-dropdown")).toBeVisible({
      timeout: 5000,
    });

    // Get all options
    const allOptions = await page
      .locator(".ant-select-item-option-content")
      .allInnerTexts();
    console.log(`Found ${allOptions.length} type options in dropdown`);
    console.log(`First 3 types:`, allOptions.slice(0, 3));

    // Verify we have options
    expect(allOptions.length).toBeGreaterThan(0);
  });

  test("should create cost element using first available type", async ({
    page,
    request,
  }) => {
    test.setTimeout(90000);

    // Get auth token
    const authStorage = await page.evaluate(() =>
      localStorage.getItem("auth-storage")
    );
    const token = JSON.parse(authStorage!).state.token;
    const headers = { Authorization: `Bearer ${token}` };

    // Get first project with WBEs
    const projResponse = await request.get(
      "http://localhost:8020/api/v1/projects?page=1&per_page=10",
      { headers }
    );
    const projData = await projResponse.json();
    const project = projData.items[0];

    // Get first WBE for project
    const wbeResponse = await request.get(
      `http://localhost:8020/api/v1/wbes?project_id=${project.project_id}&branch=main`,
      { headers }
    );
    const wbes = await wbeResponse.json();
    const wbeList = Array.isArray(wbes) ? wbes : wbes.items || [];
    const wbe = wbeList[0];

    console.log(`Creating cost element in WBE: ${wbe.code}`);

    // Navigate to WBE detail page
    await page.goto(`/projects/${project.project_id}/wbes/${wbe.wbe_id}`);
    await expect(
      page.getByRole("heading", { name: "WBE Details" })
    ).toBeVisible({
      timeout: 15000,
    });

    // Open modal
    await page.waitForTimeout(500);
    await page.click('button:has-text("Add Cost Element")');
    await expect(page.locator(".ant-modal-body").last()).toBeVisible({
      timeout: 10000,
    });

    // Fill in form fields
    const timestamp = Date.now();
    const elementName = `Test CE ${timestamp}`;
    const elementCode = `TCE${timestamp}`.substring(0, 10);

    await page.fill('input[id="cost_element_form_name"]', elementName);
    await page.fill('input[id="cost_element_form_code"]', elementCode);
    await page.locator("#cost_element_form_budget_amount").fill("5000");

    // Select first available type
    await page.click('input[id="cost_element_form_cost_element_type_id"]');
    await expect(page.locator(".ant-select-dropdown")).toBeVisible();
    await page.waitForTimeout(1000);

    // Click first option
    const firstOption = page.locator(".ant-select-item-option-content").first();
    await expect(firstOption).toBeVisible({ timeout: 10000 });
    const firstOptionText = await firstOption.innerText();
    console.log(`Selecting first type: ${firstOptionText}`);
    await firstOption.click();

    // Submit
    await page.click('button:has-text("Create")');

    // Verify creation
    await expect(page.locator(`text=${elementCode}`)).toBeVisible({
      timeout: 15000,
    });

    console.log(`✓ Successfully created cost element: ${elementCode}`);
  });
});
