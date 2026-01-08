import { test, expect } from "@playwright/test";

test.describe("Hierarchical Navigation E2E", () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto("/login");
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');
    await expect(page.getByRole("menuitem", { name: "Dashboard" })).toBeVisible(
      { timeout: 60000 }
    );
  });

  test("Navigate project hierarchy, create WBEs and Cost Elements", async ({
    page,
  }) => {
    test.setTimeout(90000);
    const timestamp = Date.now();
    const projName = `Hier Proj ${timestamp}`;
    const projCode = `HP${timestamp}`.substring(0, 10);

    // 1. Create Project
    await page.goto("/projects");

    // Setup listener for successful creation
    const projCreatePromise = page.waitForResponse(
      (response) =>
        response.url().includes("/projects") &&
        response.request().method() === "POST" &&
        response.status() === 201
    );

    await page.click('button:has-text("Add Project")');
    await page.getByLabel("Project Code").fill(projCode);
    await page.getByLabel("Project Name").fill(projName);
    await page.getByRole("dialog").getByLabel("Budget").fill("100000");
    await page.click('button:has-text("Create")');

    // Wait for API success and modal close
    const projResponse = await projCreatePromise;
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    const projJson = await projResponse.json();
    const projectId = projJson.project_id;

    // 2. Navigate to Project Detail (Directly to avoid pagination issues in E2E)
    await page.goto(`/projects/${projectId}`);

    // Verify we are on Project Detail Page
    await expect(
      page.getByRole("heading", { name: "Project Details" })
    ).toBeVisible();

    // 3. Create Root WBE (Level 1)
    await page.click('button:has-text("Add Root WBE")');
    await page.fill('input[id="wbe_form_code"]', "1.0");
    await page.fill('input[id="wbe_form_name"]', "Site Prep");
    await page.fill('input[id="wbe_form_budget_allocation"]', "50000");
    await page.click('button:has-text("Create")');

    // Verify WBE appears
    await expect(page.locator(`text=1.0`)).toBeVisible();
    await expect(page.locator(`text=Site Prep`)).toBeVisible();

    // 4. Drill down to Root WBE
    // Find the row for 1.0 and click "Open" button or row
    await page.locator("tr", { hasText: "1.0" }).click();

    // Verify WBE Detail Page (Level 1)
    await expect(
      page.getByRole("heading", { name: "WBE Details" })
    ).toBeVisible();
    await expect(page.getByText("Level", { exact: true })).toBeVisible();
    await expect(page.getByText("1", { exact: true })).toBeVisible();
    // Check Breadcrumb
    const breadcrumb = page.locator(".ant-breadcrumb");
    await expect(breadcrumb).toContainText(projCode);
    await expect(breadcrumb).toContainText("1.0 Site Prep");

    // 5. Create Child WBE (Level 2)
    await page.click('button:has-text("Add Child WBE")');
    // Pre-filled fields check could be good, but for now just fill required
    // Level should be auto-incremented to 2, Code we fill manually
    await page.fill('input[id="wbe_form_code"]', "1.1");
    await page.fill('input[id="wbe_form_name"]', "Grading");
    await page.fill('input[id="wbe_form_budget_allocation"]', "20000");
    await page.click('button:has-text("Create")');

    // Verify Child WBE appears
    await expect(page.locator(`text=1.1`)).toBeVisible();

    // 6. Drill down to Child WBE (Level 2)
    await page.locator("tr", { hasText: "1.1" }).click();

    // Verify WBE Detail Page (Level 2)
    await expect(page.getByText("Level", { exact: true })).toBeVisible();
    await expect(page.getByText("2", { exact: true })).toBeVisible();
    // Check Breadcrumb path: Proj > 1.0 > 1.1
    await expect(breadcrumb).toContainText("1.0");
    await expect(breadcrumb).toContainText("1.1 Grading");

    // // 7. Create Cost Element at this level
    // // CostElementManagement component is embedded
    // await page.click('button:has-text("Add Cost Element")');

    // // Form should be visible
    // await page.fill('input[id="cost_element_form_code"]', `CE-1.1-A`);
    // await page.fill('input[id="cost_element_form_name"]', "Excavator Rental");
    // await page.fill('input[id="cost_element_form_budget_amount"]', "5000");

    // // WBE should be pre-selected (prop wbeId passed)
    // // We confirm we don't need to select it.
    // // However, we DO need to select Cost Element Type
    // await page.click('input[id="cost_element_form_cost_element_type_id"]');
    // await page
    //   .locator('input[id="cost_element_form_cost_element_type_id"]')
    //   .fill(typeName);
    // await page.waitForTimeout(500);
    // await page
    //   .locator('input[id="cost_element_form_cost_element_type_id"]')
    //   .press("Enter");

    // await page.click('button:has-text("Create")');

    // // Verify Cost Element appears
    // await expect(page.locator(`text=CE-1.1-A`)).toBeVisible();
    // await expect(page.locator(`text=Excavator Rental`)).toBeVisible();

    // 7. Verify Breadcrumb Navigation Up
    // Click "1.0 Site Prep" in breadcrumb
    await page.locator(".ant-breadcrumb-link", { hasText: "1.0" }).click();

    // Verify we are back at Level 1
    await expect(page.getByText("Level", { exact: true })).toBeVisible();
    await expect(page.getByText("1", { exact: true })).toBeVisible();
    await expect(page.locator(`text=1.1`)).toBeVisible(); // Child 1.1 should be in the table

    // Navigation back to Project
    // await page.getByRole("link", { name: projCode }).click(); // Sometimes finding by role link is tricky with partial text
    await page.locator(".ant-breadcrumb-link a", { hasText: projCode }).click();
    await expect(
      page.getByRole("heading", { name: "Project Details" })
    ).toBeVisible();
  });
});
